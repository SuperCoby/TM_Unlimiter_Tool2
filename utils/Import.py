"""Pure-Python ManiaPlanet .Item.Gbx mesh parser/importer.

Hand-ported from GBX.NET's own reader (github.com/BigBang1112/gbx-net) --
this replaces the old bundled .NET exe (utils/Dotnet.py) as the
.Item.Gbx -> Blender mesh conversion step, so no external process/tool is
needed anymore. Entry point: import_item_gbx(filepath).
"""

import struct
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

# Nadeo/GBX geometry is Y-up (X-right, Y-up, Z-forward); Blender is Z-up
# (X-right, Z-up, Y-forward). Converts (x, y, z) -> (x, -z, y), matching the
# reference BigBang1112/blender-gbx-tools importer's visual.py exactly (a
# proper rotation, determinant +1, so face winding needs no correction).
_COORD_CONVERT = Matrix((
    (1, 0, 0, 0),
    (0, 0, -1, 0),
    (0, 1, 0, 0),
    (0, 0, 0, 1),
))

# TMNF .Solid.Gbx: same axes as tmunlimiter_blender_plugin's exporter, which
# writes game (X, Y, Z) = Blender (y, z, x) -- so Blender (x, y, z) = game
# (Z, X, Y). Imported blocks land on the tmunlimiter block-unit grid (positive
# X/Y) and re-export unchanged. Also a proper rotation (determinant +1).
_TMUNLIMITER_CONVERT = Matrix((
    (0, 0, 1, 0),
    (1, 0, 0, 0),
    (0, 1, 0, 0),
    (0, 0, 0, 1),
))

# GBX filenames chain multiple type suffixes (e.g. "Foo.Item.Gbx" or, for
# items that only reference an external sibling mesh, "Foo.Mesh.Gbx") --
# strip all of them, not just the last one, so the imported object is just
# named "Foo" regardless of which of these it was.
_KNOWN_GBX_SUFFIXES = {
    "gbx", "item", "mesh", "block", "prefab", "shape",
    "solid2", "solid", "edclassic", "edroad", "edclip",
}


def _find_file_ignore_case(base_dir, relative_path):
    """Resolve a path stored by the game ("Meshes\\Foo.Mesh.gbx": Windows
    separators, case not always matching the real file) on any OS: on
    Linux/macOS file names are case-sensitive and "\\" isn't a separator."""
    path = Path(base_dir)
    for part in relative_path.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            path = path.parent
            continue
        candidate = path / part
        if not candidate.exists() and path.is_dir():
            candidate = next((child for child in path.iterdir() if child.name.lower() == part.lower()), candidate)
        path = candidate
    return path


def _strip_gbx_suffixes(filename):
    parts = filename.split(".")
    while len(parts) > 1 and parts[-1].lower() in _KNOWN_GBX_SUFFIXES:
        parts.pop()
    return ".".join(parts)


# =======================================================================
# LZO1X decompressor -- pure-Python, independently implemented from the
# public LZO1X compressed-block format (instruction bit layout, length
# and distance formulas). GBX file bodies are LZO1X-compressed.
# =======================================================================

def _lzo1x_decompress(src: bytes, dst_size: int) -> bytes:
    dst = bytearray()
    ip = 0
    state = 0

    first = src[ip]
    if first >= 18:
        length = first - 17
        ip += 1
        dst.extend(src[ip:ip + length])
        ip += length
        state = 4 if first >= 22 else length

    while True:
        inst = src[ip]
        ip += 1

        if inst & 0xC0:  # M2: 3-8 byte copy, <=2kB distance
            next_byte = src[ip]
            ip += 1
            if inst & 0x80:
                length = 5 + ((inst >> 5) & 3)
            else:
                length = 3 + ((inst >> 5) & 1)
            distance = (next_byte << 3) + ((inst >> 2) & 7) + 1
            state = inst & 3
            m_pos = len(dst) - distance
            for _ in range(length):
                dst.append(dst[m_pos])
                m_pos += 1

        elif inst & 0x20:  # M3: variable-length copy, <=16kB distance
            length = 2 + (inst & 0x1F)
            if length == 2:
                zero_count = 0
                while src[ip] == 0:
                    zero_count += 1
                    ip += 1
                length += zero_count * 255 + 31 + src[ip]
                ip += 1
            d = src[ip] | (src[ip + 1] << 8)
            ip += 2
            state = d & 3
            distance = (d >> 2) + 1
            m_pos = len(dst) - distance
            for _ in range(length):
                dst.append(dst[m_pos])
                m_pos += 1

        elif inst & 0x10:  # M4: variable-length copy, 16-48kB distance
            length = 2 + (inst & 7)
            if length == 2:
                zero_count = 0
                while src[ip] == 0:
                    zero_count += 1
                    ip += 1
                length += zero_count * 255 + 7 + src[ip]
                ip += 1
            d = src[ip] | (src[ip + 1] << 8)
            ip += 2
            state = d & 3
            distance = 16384 + ((inst & 8) << 11) + (d >> 2)
            if distance == 16384:
                break  # end-of-stream marker
            m_pos = len(dst) - distance
            for _ in range(length):
                dst.append(dst[m_pos])
                m_pos += 1

        else:  # M1 family (inst < 16): meaning depends on `state`
            if state == 0:
                # Fresh literal run (no preceding match to draw a short
                # copy's distance from yet).
                length = 3 + inst
                if length == 3:
                    zero_count = 0
                    while src[ip] == 0:
                        zero_count += 1
                        ip += 1
                    length += zero_count * 255 + 15 + src[ip]
                    ip += 1
                dst.extend(src[ip:ip + length])
                ip += length
                state = 4
                continue
            elif state != 4:
                next_byte = src[ip]
                ip += 1
                distance = (inst >> 2) + (next_byte << 2) + 1
                length = 2
                state = inst & 3
            else:
                next_byte = src[ip]
                ip += 1
                distance = (inst >> 2) + (next_byte << 2) + 2049
                length = 3
                state = inst & 3
            m_pos = len(dst) - distance
            for _ in range(length):
                dst.append(dst[m_pos])
                m_pos += 1

        if state:
            dst.extend(src[ip:ip + state])
            ip += state

    if len(dst) != dst_size:
        raise ValueError(f"LZO1X decompress size mismatch: got {len(dst)}, expected {dst_size}")

    return bytes(dst)


# =======================================================================
# GBX binary reader -- primitives + the generic chunk-loop / NodeRef
# resolution mechanism shared by every GBX class (mirrors GBX.NET's own
# CMwNod.Read loop and GbxReader primitives).
# =======================================================================

_SKIP_MARKER = 0x534B4950
_FACADE = 0xFACADE01


class _GbxReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.id_version = None
        self.id_dict = {}
        self.node_dict = {}
        self.external = {}  # node index -> relative file path (ref table)

    def bytes(self, n):
        b = self.data[self.pos:self.pos + n]
        if len(b) != n:
            raise EOFError(f"wanted {n} bytes at {self.pos}, got {len(b)}")
        self.pos += n
        return b

    def u8(self):
        return self.bytes(1)[0]

    def bool(self):
        return self.u32() != 0

    def bool_byte(self):
        return self.u8() != 0

    def u16(self):
        return struct.unpack_from("<H", self.bytes(2))[0]

    def i32(self):
        return struct.unpack_from("<i", self.bytes(4))[0]

    def u32(self):
        return struct.unpack_from("<I", self.bytes(4))[0]

    def f32(self):
        return struct.unpack_from("<f", self.bytes(4))[0]

    def vec2(self):
        return (self.f32(), self.f32())

    def vec3(self):
        return (self.f32(), self.f32(), self.f32())

    def box_aligned(self):
        return (self.f32(), self.f32(), self.f32(), self.f32(), self.f32(), self.f32())

    def iso4(self):
        return {
            "XX": self.f32(), "XY": self.f32(), "XZ": self.f32(),
            "YX": self.f32(), "YY": self.f32(), "YZ": self.f32(),
            "ZX": self.f32(), "ZY": self.f32(), "ZZ": self.f32(),
            "TX": self.f32(), "TY": self.f32(), "TZ": self.f32(),
        }

    def array_i32(self, count=None):
        if count is None:
            count = self.i32()
        return [self.i32() for _ in range(count)]

    def array_f32(self, count=None):
        if count is None:
            count = self.i32()
        return [self.f32() for _ in range(count)]

    def array_vec3(self, count=None):
        if count is None:
            count = self.i32()
        return [self.vec3() for _ in range(count)]

    def array_int2(self, count):
        return [(self.i32(), self.i32()) for _ in range(count)]

    def optimized_int(self, determine_from):
        d = determine_from & 0xFFFFFFFF
        if d > 0xFFFF:
            return self.i32()
        if d > 0xFF:
            return self.u16()
        return self.u8()

    def array_optimized_int(self, length=None, determine_from=None):
        if length is None:
            length = self.i32()
        if length == 0:
            return []
        d = (determine_from if determine_from is not None else length) & 0xFFFFFFFF
        if d >= 0xFFFF:
            return self.array_i32(length)
        if d >= 0xFF:
            return [self.u16() for _ in range(length)]
        return [self.u8() for _ in range(length)]

    def array_optimized_int2(self, length=None, determine_from=None):
        if length is None:
            length = self.i32()
        if length == 0:
            return []
        d = (determine_from if determine_from is not None else length) & 0xFFFFFFFF
        if d >= 0xFFFF:
            return self.array_int2(length)
        if d >= 0xFF:
            out = []
            for _ in range(length):
                x = self.i32()
                out.append((x & 0xFFFF, (x >> 16) & 0xFFFF))
            return out
        out = []
        for _ in range(length):
            x = self.u16()
            out.append((x & 0xFF, (x >> 8) & 0xFF))
        return out

    def array_readable(self, read_fn, count=None, **kwargs):
        if count is None:
            count = self.i32()
        return [read_fn(self, **kwargs) for _ in range(count)]

    def string(self):
        length = self.i32()
        if length == 0:
            return ""
        return self.bytes(length).decode("utf-8", errors="replace")

    def read_id_as_string(self):
        # GBX's shared "lookback string table": the very first Id read in
        # the whole file also consumes a lazily-initialized IdVersion int.
        if self.id_version is None:
            self.id_version = self.i32()
            if self.id_version < 3:
                raise ValueError(f"unsupported Id version {self.id_version}")

        index = self.u32()

        if index == 0xFFFFFFFF:
            return ""

        if (index & 0xC0000000) not in (0x40000000, 0x80000000):
            return str(index)

        if (index & 0x3FFFFFFF) != 0:
            return self.id_dict.get(index, "")

        s = self.string()
        self.id_dict[index + len(self.id_dict) + 1] = s
        return s

    def read_ident(self):
        idname = self.read_id_as_string()
        collection = self.read_id_as_string()
        author = self.read_id_as_string()
        return {"Id": idname, "Collection": collection, "Author": author}

    def read_node_ref(self, node_parsers, archive_parsers=None):
        index = self.i32()
        if index == -1:
            return None
        if index in self.external:
            # Node stored in another file (ref table), e.g. a TMNF
            # .Material.Gbx: only its relative path is known.
            return {"_external": self.external[index]}
        if index in self.node_dict:
            return self.node_dict[index]

        raw_class_id = self.u32()
        if raw_class_id == 0xFFFFFFFF:
            return None

        class_id = raw_class_id
        node = {"_class": class_id, "_class_hex": f"0x{class_id:08X}"}
        self.node_dict[index] = node

        archive_fn = archive_parsers.get(class_id) if archive_parsers else None
        if archive_fn is not None:
            archive_fn(self, node)
        else:
            parser = node_parsers.get(class_id)
            if parser is None:
                raise ValueError(
                    f"no parser registered for class {node['_class_hex']} "
                    f"(referenced at pos {self.pos})"
                )
            _read_node_body(self, node, node_parsers, parser)

        return node

    def read_array_node_ref(self, node_parsers, archive_parsers=None):
        count = self.i32()
        return [self.read_node_ref(node_parsers, archive_parsers) for _ in range(count)]


def _read_node_body(r, node, node_parsers, parser):
    """Generic CMwNod.Read loop: repeatedly read a chunk id, dispatch to a
    known per-class-chunk handler if we have one, otherwise skip (if the
    chunk is wrapped as skippable) or raise (if it's an unknown chunk we'd
    need exact field-layout knowledge for, which we don't have)."""
    while True:
        raw_chunk_id = r.u32()

        if raw_chunk_id == _FACADE:
            return

        chunk_id = raw_chunk_id
        handler = None
        if parser is not None:
            handler = parser.get(chunk_id)

        if handler is not None and not handler[0]:
            # Non-skippable chunk: must be parsed exactly, no size prefix --
            # unless the file actually stores it as skippable (the .chunkl
            # schemas don't always say which), then fall through below.
            if struct.unpack_from("<I", r.data, r.pos)[0] != _SKIP_MARKER:
                handler[1](r, node)
                continue

        # Skippable (known or unknown): expect a SKIP marker + size.
        marker = r.u32()
        if marker != _SKIP_MARKER:
            raise ValueError(
                f"chunk 0x{chunk_id:08X} on class {node.get('_class_hex')} "
                f"expected skippable but no SKIP marker at pos {r.pos - 4} "
                f"(got 0x{marker:08X}) -- likely a non-skippable chunk we "
                f"don't have a handler for yet"
            )
        size = r.i32()
        start = r.pos
        r.chunk_end = start + size  # lets a handler check where its chunk ends
        if handler is not None:
            handler[1](r, node)
            consumed = r.pos - start
            if consumed != size:
                raise ValueError(
                    f"chunk 0x{chunk_id:08X} handler consumed {consumed} "
                    f"bytes but chunk size was {size}"
                )
        else:
            r.bytes(size)


# =======================================================================
# Per-class chunk parsers, hand-ported from the GBX.NET .chunkl schema
# files (github.com/BigBang1112/gbx-net) and, where that local schema
# turned out stale, from GBX.NET's own hand-written CPlugCrystal.cs
# reader and verified byte-for-byte against real files. Currently covers
# enough of CGameItemModel to reach a "customizable" item's CPlugCrystal
# mesh (the CGameCommonItemEntityModelEdition.MeshCrystal path) -- the
# CPlugSolid2Model/CPlugVisualIndexedTriangles path used by plain static
# items is not implemented yet (its local schema is too incomplete/stale
# to port reliably without much more reverse engineering).
# =======================================================================

_NODE_PARSERS = {}       # class_id -> {chunk_id: (skippable, handler)}
_ARCHIVE_PARSERS = {}    # class_id -> read_fn(r, node) for "nameless archive" node types


def _register(class_id, chunks, bases=()):
    merged = {}
    for base in bases:
        merged.update(_NODE_PARSERS[base])
    merged.update(chunks)
    _NODE_PARSERS[class_id] = merged
    return merged


def _register_archive(class_id, read_fn):
    _ARCHIVE_PARSERS[class_id] = read_fn


def _noderef(r):
    return r.read_node_ref(_NODE_PARSERS, _ARCHIVE_PARSERS)


def _array_noderef(r):
    return r.read_array_node_ref(_NODE_PARSERS, _ARCHIVE_PARSERS)


# --- CGameCtnCollector 0x2E001000 (base of CGameItemModel) -------------

def _collector_002(r, n):
    n["Ident"] = r.read_ident()


def _collector_006(r, n):
    n["SkinKind"] = r.i32()


def _collector_007(r, n):
    n["IsInternal"] = r.bool()
    n["NeedUnlock"] = r.bool()
    n["CatalogPosition"] = r.i32()
    n["NbAvailableMin"] = r.i32()
    n["CopperPrice"] = r.i32()
    n["NbAvailableMax"] = r.i32()


def _collector_008(r, n):
    n["GameSkin"] = _noderef(r)


def _collector_009(r, n):
    # The local .chunkl schema documents this chunk as empty, but real
    # files show it carries string + int + id -- confirmed byte-for-byte
    # against a real decompressed body (this is also the file's very
    # first Id read, so it's where the lazy IdVersion prefix gets
    # consumed). Field purpose unclear (base-class bookkeeping, not
    # mesh-relevant), so just consume them.
    n["_009_name"] = r.string()
    r.i32()
    r.read_id_as_string()


def _collector_00A(r, n):
    n["_00A_id"] = r.read_id_as_string()


def _collector_00B(r, n):
    n["Ident"] = r.read_ident()


def _collector_00C(r, n):
    n["Name"] = r.string()


def _collector_00D(r, n):
    n["Description"] = r.string()


def _collector_00E(r, n):
    n["IconUseAutoRender"] = r.bool()
    n["IconQuarterRotationY"] = r.i32()


def _collector_010(r, n):
    version = r.i32()
    r.i32()  # DefaultSkin (external) NodeRef index, expected -1 for standalone files
    skin_dir = r.string()
    n["SkinDirectory"] = skin_dir
    if version >= 2:
        if not skin_dir:
            r.i32()  # CMwNod NodeRef index, expected -1


def _collector_011(r, n):
    version = r.i32()
    n["IsInternal"] = r.bool()
    n["IsAdvanced"] = r.bool()
    n["CatalogPosition"] = r.i32()
    if version >= 1:
        n["ProdState"] = r.u8()


def _collector_012(r, n):
    r.i32()
    r.i32()
    r.i32()
    r.i32()


_register(0x2E001000, {
    0x2E001002: (False, _collector_002),
    0x2E001006: (False, _collector_006),
    0x2E001007: (False, _collector_007),
    0x2E001008: (False, _collector_008),
    0x2E001009: (False, _collector_009),
    0x2E00100A: (False, _collector_00A),
    0x2E00100B: (False, _collector_00B),
    0x2E00100C: (False, _collector_00C),
    0x2E00100D: (False, _collector_00D),
    0x2E00100E: (False, _collector_00E),
    0x2E001010: (False, _collector_010),
    0x2E001011: (False, _collector_011),
    0x2E001012: (False, _collector_012),
})


# --- CPlugStaticObjectModel 0x09159000 (kept registered so NodeRef
#     lookups toward it don't hard-fail; its own geometry isn't parsed) --

def _static_object_model_archive(r, n):
    n["Version"] = r.i32()
    n["Mesh"] = _noderef(r)
    is_collidable = r.u8() != 0
    n["IsMeshCollidable"] = is_collidable
    if not is_collidable:
        n["Shape"] = _noderef(r)


_register_archive(0x09159000, _static_object_model_archive)


# --- CGameCommonItemEntityModelEdition 0x2E026000 -----------------------

def _entity_model_edition_000(r, n):
    version = r.i32()
    n["ItemType"] = r.i32()
    n["MeshCrystal"] = _noderef(r)
    r.string()  # U01
    n["U02"] = _noderef(r)
    count = r.i32()
    for _ in range(count):
        _noderef(r)  # CPlugFileImg[]
    count = r.i32()
    for _ in range(count):
        r.vec3(); r.bool(); r.f32()  # SpriteParam[]
    _noderef(r)  # CPlugParticleEmitterModel
    _noderef(r)  # CPlugAnimLocSimple
    count = r.i32()
    for _ in range(count):
        r.i32(); r.f32(); r.f32(); r.f32(); r.f32(); r.f32(); r.f32(); r.f32()  # LightBallStateSimple[]
    for _ in range(7):
        r.f32()  # U07..U13
    r.iso4()  # U14
    if version >= 3 and n["ItemType"] == 2:  # PickUp
        n["Mass"] = r.f32()
    u15 = r.bool()
    if not u15:
        _noderef(r)  # U16 CPlugCrystal
    u17 = r.bool()
    if u17:
        r.i32()   # int? U18 -- presence already gated by "if U17"
        r.iso4()  # iso4? U19 -- presence already gated by "if U17"
    r.i32()  # U20
    if version >= 1:
        n["InventoryName"] = r.string()
        n["InventoryDescription"] = r.string()
        n["InventoryItemClass"] = r.i32()
        n["InventoryOccupation"] = r.i32()
        if version >= 6:
            if version <= 6:
                _noderef(r)  # U21
            if version >= 7 and n["ItemType"] == 2:
                r.bool()  # U22


def _entity_model_edition_001(r, n):
    pass


_register(0x2E026000, {
    0x2E026000: (False, _entity_model_edition_000),
    0x2E026001: (True, _entity_model_edition_001),
})


# --- CGameItemModel 0x2E002000 (inherits CGameCtnCollector) -------------

def _item_type_version(item_type):
    """GetItemTypeVersion from CGameItemModel.Chunk2E002019: the version
    threshold below which the legacy phyModelCustom/visModelCustom fields
    are present, per item type."""
    if item_type in (1, 2):
        return 9
    if item_type == 4:
        return 10
    if item_type == 5:
        return 9
    if item_type == 11:
        return None
    return 12


def _item_model_019(r, n):
    version = r.i32()

    item_type = n.get("_item_type")
    threshold = _item_type_version(item_type if item_type is not None else 0)
    if threshold is not None and version < threshold:
        n["PhyModelCustom"] = _noderef(r)
        n["VisModelCustom"] = _noderef(r)

    if version >= 3:
        n["DefaultWeaponName"] = r.read_id_as_string()
        if version >= 4:
            if n.get("PhyModelCustom") is not None:
                r.i32()
            else:
                n["PhyModelCustom"] = _noderef(r)
            if version >= 5:
                if n.get("VisModelCustom") is not None:
                    r.i32()
                else:
                    n["VisModelCustom"] = _noderef(r)
                if version >= 6:
                    n["Actions"] = _array_noderef(r)
                    if version >= 7:
                        n["DefaultCam"] = r.i32()
                        if version >= 8:
                            n["EntityModelEdition"] = _noderef(r)
                            if n["EntityModelEdition"] is None:
                                n["EntityModel"] = _noderef(r)
                            if version >= 13:
                                n["VFX"] = _noderef(r)
                                if version >= 15:
                                    n["MaterialModifier"] = _noderef(r)


def _item_model_008(r, n):
    n["NadeoSkinFids"] = _array_noderef(r)


def _item_model_009(r, n):
    r.i32()  # version (the "_deprec" array format is versioned)
    n["Cameras"] = _array_noderef(r)


def _item_model_00C(r, n):
    n["RaceInterfaceFid"] = _noderef(r)


def _item_model_012(r, n):
    n["GroundPoint"] = r.vec3()
    n["PainterGroundMargin"] = r.f32()
    n["OrbitalCenterHeightFromGround"] = r.f32()
    n["OrbitalRadiusBase"] = r.f32()
    n["OrbitalPreviewAngle"] = r.f32()


def _item_model_013(r, n):
    n["AudioEnvironmentInCar"] = _noderef(r)


def _item_model_015(r, n):
    n["ItemTypeE"] = r.i32()


def _item_model_01A(r, n):
    n["_01A"] = _noderef(r)


def _item_model_01B(r, n):
    n["_01B"] = _noderef(r)


def _item_model_01C(r, n):
    version = r.i32()
    if version >= 5:
        n["DefaultPlacement"] = _noderef(r)
        return
    n["_01C_positions"] = r.array_vec3()
    if version >= 1:
        for _ in range(6):
            r.f32()
        if version >= 2:
            for _ in range(5):
                r.f32()
            if version >= 3:
                r.f32()
                r.f32()
                if version >= 4:
                    r.f32()


def _item_model_01D(r, n):
    r.u16()  # short


def _item_model_01E(r, n):
    version = r.i32()
    if version >= 2:
        archetype_ref = r.string()
        n["ArchetypeRef"] = archetype_ref
        if version >= 5:
            if not archetype_ref:
                n["ArchetypeFid"] = _noderef(r)
            if version >= 6:
                r.string()  # SkinDirNameCustom
                if version >= 7:
                    r.i32()  # -1


def _item_model_01F(r, n):
    version = r.i32()
    if version <= 6:
        if version >= 5:
            r.string()
            r.string()
            r.i32()
        if version >= 4:
            r.i32()
        if version <= 2:
            r.u16()
    n["WaypointType"] = r.i32()
    if version <= 7:
        r.iso4()
    if version >= 6:
        n["DisableLightmap"] = r.bool()
        if version >= 9:
            if version <= 12:
                _noderef(r)
            if version >= 11:
                r.u8()
                if version >= 12:
                    r.i32()
                    r.i32()


def _item_model_020(r, n):
    version = r.i32()
    if version <= 1:
        r.string()
        _noderef(r)
        return
    n["IconFid"] = r.string()
    if version >= 3:
        r.bool_byte()


def _read_item_group_element(r):
    location = r.iso4()
    item_ref = r.string()
    item = _noderef(r) if not item_ref else None
    return {"Location": location, "ItemRef": item_ref, "Item": item}


def _item_model_021(r, n):
    r.i32()  # version
    n["ItemGroupElements"] = r.array_readable(_read_item_group_element)


def _item_model_023(r, n):
    r.i32()  # version
    r.u8()
    r.i32()


_register(0x2E002000, {
    0x2E002008: (False, _item_model_008),
    0x2E002009: (False, _item_model_009),
    0x2E00200C: (False, _item_model_00C),
    0x2E002012: (False, _item_model_012),
    0x2E002013: (False, _item_model_013),
    0x2E002015: (False, _item_model_015),
    0x2E002019: (False, _item_model_019),
    0x2E00201A: (False, _item_model_01A),
    0x2E00201B: (False, _item_model_01B),
    0x2E00201C: (False, _item_model_01C),
    0x2E00201D: (False, _item_model_01D),
    0x2E00201E: (False, _item_model_01E),
    0x2E00201F: (False, _item_model_01F),
    0x2E002020: (False, _item_model_020),
    0x2E002021: (False, _item_model_021),
    0x2E002023: (False, _item_model_023),
}, bases=(0x2E001000,))


# --- CGameItemPlacementParam 0x2E020000 -- every chunk is (skippable)
#     with no field-level logic we need, so the generic skip-by-size path
#     handles all of them; just register the class for NodeRef lookups. --

_register(0x2E020000, {})


# --- CPlugCrystal 0x09003000 (inherits CPlugTreeGenerator 0x09051000),
#     hand-ported from GBX.NET's own CPlugCrystal.cs reader -- the
#     auto-generated .chunkl schema for the "Crystal" struct is a stale
#     stub, so this hand-written logic is what's actually authoritative. -

def _tree_generator_000(r, n):
    r.u32()


_register(0x09051000, {
    0x09051000: (False, _tree_generator_000),
})


def _read_material_archive(r):
    name = r.string()
    user_inst = None
    if not name:
        user_inst = _noderef(r)
    return {"MaterialName": name, "MaterialUserInst": user_inst}


# Nadeo prefixes some material names with a technical tag (e.g.
# "_TDSN_StadiumRoadBorder_Concrete") that's meaningless for a Blender
# material list -- strip it for display.
_MATERIAL_NAME_PREFIXES_TO_STRIP = ("_TDSN_",)


def _clean_material_name(name):
    if not name:
        return name
    for prefix in _MATERIAL_NAME_PREFIXES_TO_STRIP:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break

    # CPlugSolid2Model.MaterialIds sometimes carries the actual material
    # name wrapped in a technical collector-id form instead of the plain
    # name, e.g. "MP_Stadium_StadiumSculpt2_asset" for "StadiumSculpt2" --
    # unwrap it so it matches the plain names used elsewhere (e.g. AutoMat's
    # material_list).
    if name.startswith("MP_") and name.endswith("_asset"):
        parts = name.split("_", 2)
        if len(parts) == 3:
            name = parts[2][:-len("_asset")]

    return name


def _material_display_name(mat):
    """Resolve a Crystal face's Material dict down to a display string."""
    if not mat:
        return None
    name = mat.get("MaterialName")
    if not name:
        user_inst = mat.get("MaterialUserInst")
        name = user_inst.get("_material_name") if user_inst else None
    return _clean_material_name(name)


def _read_visual_level_archive(r):
    return {"_a": r.i32(), "_b": r.f32()}


def _read_anchor_info_archive(r):
    return {
        "_a": r.bool(), "_b": r.bool(), "iso4": r.iso4(),
        "_s": r.string(), "_i": r.i32(),
    }


def _read_part_archive(r, version):
    part = {}
    if version >= 31:
        part["U01"] = r.i32()
    if version >= 36:
        part["U02"] = r.u8()
    elif version <= 35:
        part["U02"] = r.i32()
    part["U03"] = r.i32()
    part["Name"] = r.string()
    part["U04"] = r.i32()
    part["U05"] = r.array_i32()
    return part


def _read_layer_base(r):
    ver = r.i32()
    crystal_enabled = r.bool()
    layer_id = r.read_id_as_string()
    layer_name = r.string()
    is_enabled = True
    if ver >= 1:
        is_enabled = r.bool()
    return {"Ver": ver, "CrystalEnabled": crystal_enabled, "LayerId": layer_id,
            "LayerName": layer_name, "IsEnabled": is_enabled}


def _read_part_in_layer(r):
    return {"GroupIndex": r.i32(), "LayerId": r.read_id_as_string()}


def _read_modifier_base(r):
    layer = _read_layer_base(r)
    layer["ModifierVersion"] = r.i32()
    layer["Mask"] = r.array_readable(_read_part_in_layer)
    return layer


def _read_crystal_struct(r, crystal_node):
    c = {}
    version = r.i32()
    c["Version"] = version

    visual_levels = []
    if version >= 13:
        c["U01"] = r.i32()
        visual_levels = r.array_readable(_read_visual_level_archive)
    c["VisualLevels"] = visual_levels

    anchor_infos = []
    if version >= 23:
        anchor_infos = r.array_readable(_read_anchor_info_archive)
    c["AnchorInfos"] = anchor_infos

    groups = []
    if version >= 22:
        groups = r.array_readable(_read_part_archive, version=version)
    c["Groups"] = groups

    if version < 21:
        raise ValueError(f"Crystal version {version} not supported")

    is_embedded = False
    if version >= 25:
        if version < 29:
            r.bool()
            r.bool()
        is_embedded = r.bool_byte() if version >= 34 else r.bool()
        if version >= 33:
            c["U02"] = r.i32()
            c["U03"] = r.i32()

    if not is_embedded:
        raise ValueError("Crystal.Gbx (non-embedded) is not supported")

    has_faced_edges = version < 35

    positions = r.array_vec3()
    c["Positions"] = positions

    edge_count = r.i32()
    if has_faced_edges:
        edges = r.array_int2(edge_count)
    else:
        edges = r.array_optimized_int2()
    c["Edges"] = edges

    face_count = r.i32()

    tex_coords = []
    tex_coord_indices = []
    faces = []
    face_vertex_index = 0

    if version >= 37:
        tex_coord_count = r.i32()
        tex_coords = [r.vec2() for _ in range(tex_coord_count)]
        tex_coord_indices = r.array_optimized_int()

    for _i in range(face_count):
        if version >= 35:
            vert_count = r.u8() + 3
        else:
            vert_count = r.i32()

        if version >= 34:
            inds = r.array_optimized_int(vert_count, len(positions))
        else:
            inds = r.array_i32(vert_count)

        vertices = [None] * vert_count

        if version < 27:
            uv_count = min(r.i32(), vert_count)
            for j in range(uv_count):
                vertices[j] = {"Index": inds[j], "TexCoord": r.vec2()}
            for j in range(uv_count, vert_count):
                vertices[j] = {"Index": inds[j], "TexCoord": (0.0, 0.0)}
            r.vec3()  # normal?
        elif version < 37:
            for j in range(vert_count):
                vertices[j] = {"Index": inds[j], "TexCoord": r.vec2()}
        else:
            for j in range(vert_count):
                tc = tex_coords[tex_coord_indices[face_vertex_index]]
                face_vertex_index += 1
                vertices[j] = {"Index": inds[j], "TexCoord": tc}

        material_index = -1
        if version >= 25:
            if version >= 33 and len(crystal_node.get("Materials") or []) > 0:
                material_index = r.optimized_int(len(crystal_node["Materials"]))
            else:
                material_index = r.i32()

        if version >= 33:
            group_index = r.optimized_int(len(groups))
        else:
            group_index = r.i32()

        materials = crystal_node.get("Materials") or []
        material = None if (len(materials) == 0 or material_index == -1) else materials[material_index]

        faces.append({
            "Vertices": vertices,
            "Group": groups[group_index] if group_index < len(groups) else None,
            "Material": material,
        })

    for _face in faces:
        if not is_embedded:
            r.i32()
        if version < 30 or not is_embedded:
            r.i32()
        if version >= 22 and not is_embedded:
            r.i32()

    if version < 29:
        for _pos in positions:
            r.f32()

    c["U04"] = r.i32()

    if 7 <= version < 32:
        crystal_link_length = r.i32()
        if crystal_link_length > 0:
            raise ValueError("CCrystalLink array length > 0 not supported")
        if version >= 10:
            c["U05"] = r.i32()
            c["U06"] = r.string()
            if version < 30:
                r.array_f32()

    if version < 36:
        num_faces = r.i32()
        num_edges = r.i32()
        num_verts = r.i32()
        r.bytes(num_faces * 4)
        r.bytes(num_edges * 4)
        r.bytes(num_verts * 4)
        c["U07"] = r.i32()

    c["Faces"] = faces
    return c


def _read_geometry_layer(r, crystal_node):
    layer = _read_layer_base(r)
    layer["_type"] = "Geometry"
    geometry_version = r.i32()
    layer["GeometryVersion"] = geometry_version
    layer["Crystal"] = _read_crystal_struct(r, crystal_node)
    layer["U02"] = r.array_i32()
    if geometry_version >= 1:
        layer["IsVisible"] = r.bool()
        layer["Collidable"] = r.bool()
    else:
        layer["IsVisible"] = True
        layer["Collidable"] = True
    return layer


def _read_subdivide_smooth_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "SubdivideSmooth"
    layer["SubdivideSmoothVersion"] = r.i32()
    layer["Subdivisions"] = r.i32()
    return layer


def _read_translation_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "Translation"
    layer["TranslationVersion"] = r.i32()
    layer["Translation"] = r.vec3()
    return layer


def _read_rotation_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "Rotation"
    layer["RotationVersion"] = r.i32()
    layer["Rotation"] = r.f32()
    layer["Axis"] = r.i32()
    layer["Independently"] = r.bool()
    return layer


def _read_scale_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "Scale"
    layer["ScaleVersion"] = r.i32()
    layer["Scale"] = r.vec3()
    layer["Independently"] = r.bool()
    return layer


def _read_mirror_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "Mirror"
    layer["MirrorVersion"] = r.i32()
    layer["Axis"] = r.i32()
    layer["Distance"] = r.f32()
    layer["Independently"] = r.bool()
    return layer


def _read_move_to_ground_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "MoveToGround"
    layer["MoveToGroundVersion"] = r.i32()
    r.bool()
    return layer


def _read_extrude_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "Extrude"
    layer["ExtrudeVersion"] = r.i32()
    layer["Size"] = r.vec3()
    return layer


def _read_subdivide_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "Subdivide"
    layer["SubdivideVersion"] = r.i32()
    layer["Subdivisions"] = r.i32()
    return layer


def _read_chaos_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "Chaos"
    chaos_version = r.i32()
    layer["ChaosVersion"] = chaos_version
    layer["MinDistance"] = r.f32()
    r.i32()
    if chaos_version >= 1:
        layer["MaxDistance"] = r.f32()
    return layer


def _read_smooth_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "Smooth"
    layer["SmoothVersion"] = r.i32()
    r.f32()
    r.bool()
    return layer


def _read_border_transition_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "BorderTransition"
    layer["BorderTransitionVersion"] = r.i32()
    r.f32()
    r.f32()
    _array_noderef(r)  # CPlugVisual[]
    return layer


def _read_deformation_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "Deformation"
    layer["DeformationVersion"] = r.i32()
    r.box_aligned()
    r.iso4()
    return layer


def _read_cubes_layer(r, crystal_node):
    raise ValueError("CubesLayer (VoxelSpace) is not supported")


def _read_trigger_layer(r, crystal_node):
    layer = _read_layer_base(r)
    layer["_type"] = "Trigger"
    trigger_version = r.i32()
    layer["TriggerVersion"] = trigger_version
    layer["Crystal"] = _read_crystal_struct(r, crystal_node)
    if trigger_version >= 1:
        r.array_i32()
    return layer


def _read_spawn_position_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "SpawnPosition"
    spawn_version = r.i32()
    layer["SpawnPositionVersion"] = spawn_version
    layer["SpawnPosition"] = r.vec3()
    layer["HorizontalAngle"] = r.f32()
    layer["VerticalAngle"] = r.f32()
    if spawn_version >= 1:
        layer["RollAngle"] = r.f32()
    return layer


def _read_light_pos_archive(r):
    return {"_i": r.i32(), "iso4": r.iso4()}


def _read_light_layer(r, crystal_node):
    layer = _read_modifier_base(r)
    layer["_type"] = "Light"
    layer["LightVersion"] = r.i32()
    layer["Lights"] = _array_noderef(r)
    layer["LightPositions"] = r.array_readable(_read_light_pos_archive)
    return layer


_LAYER_READERS = {
    0: _read_geometry_layer,
    1: _read_subdivide_smooth_layer,
    2: _read_translation_layer,
    3: _read_rotation_layer,
    4: _read_scale_layer,
    5: _read_mirror_layer,
    6: _read_move_to_ground_layer,
    7: _read_extrude_layer,
    8: _read_subdivide_layer,
    9: _read_chaos_layer,
    10: _read_smooth_layer,
    11: _read_border_transition_layer,
    12: _read_deformation_layer,
    13: _read_cubes_layer,
    14: _read_trigger_layer,
    15: _read_spawn_position_layer,
    18: _read_light_layer,
}


def _crystal_003(r, n):
    r.i32()  # version
    n["Materials"] = r.array_readable(_read_material_archive)


def _crystal_005(r, n):
    r.i32()  # version
    layer_count = r.i32()
    layers = []
    for _ in range(layer_count):
        layer_type = r.i32()
        reader = _LAYER_READERS.get(layer_type)
        if reader is None:
            raise ValueError(f"unsupported crystal layer type {layer_type}")
        layers.append(reader(r, n))
    n["Layers"] = layers


def _crystal_006(r, n):
    version = r.i32()
    faces = [f for layer in n.get("Layers", []) if layer.get("_type") == "Geometry"
              and layer.get("IsEnabled") and layer.get("IsVisible")
              for f in layer["Crystal"]["Faces"]]

    lightmap_coord_count = r.i32()

    if version == 0:
        for face in faces:
            for v in face["Vertices"]:
                r.vec2()

    if version >= 1:
        for _ in range(lightmap_coord_count):
            r.u16()
            r.u16()

        if version >= 2:
            r.array_optimized_int()


def _crystal_007(r, n):
    r.i32()  # version
    n["SmoothingGroups"] = r.array_f32()
    r.array_i32()


_register(0x09003000, {
    0x09003003: (False, _crystal_003),
    0x09003005: (False, _crystal_005),
    0x09003006: (False, _crystal_006),
    0x09003007: (False, _crystal_007),
}, bases=(0x09051000,))


# --- CPlugMaterialUserInst 0x090FD000 -----------------------------------

def _material_user_inst_000(r, n):
    version = r.i32()
    is_using_game_material = False
    if version >= 11:
        is_using_game_material = r.bool_byte()
    n["MaterialName"] = r.read_id_as_string()
    n["Model"] = r.read_id_as_string()
    n["BaseTexture"] = r.string()
    r.u8()  # SurfacePhysicId
    if version >= 10:
        r.u8()  # SurfaceGameplayId
    link = None
    if version >= 1:
        if is_using_game_material:
            link = r.string()
        else:
            if version >= 9:
                if version <= 10:
                    link = r.string()
                else:
                    link = r.read_id_as_string()
            else:
                link = r.read_id_as_string()
        if version >= 2:
            r.array_readable(lambda rr: (rr.read_id_as_string(), rr.read_id_as_string(), rr.i32()))  # Cst[]
            r.array_i32()  # Color
            if version >= 3:
                r.array_readable(
                    lambda rr: (rr.read_id_as_string(), rr.read_id_as_string(), rr.f32(), rr.bytes(8))
                )  # UvAnim[]
                if version >= 4:
                    count = r.i32()
                    for _ in range(count):
                        r.read_id_as_string()
                    if version >= 6:
                        r.array_readable(lambda rr: (rr.i32(), rr.string()))  # UserTexture[]
                        if version >= 7:
                            r.read_id_as_string()  # HidingGroup
    n["Link"] = link
    # Link is the canonical material name (e.g. "StadiumSculpt2", or the
    # name of a linked custom material) and, empirically, is reliable even
    # when IsUsingGameMaterial is false. MaterialName is the level editor's
    # own local instance name for this particular material slot -- it's
    # frequently an arbitrary, sometimes ".001"-collided editor-assigned
    # string with no relation to the actual material, so only fall back to
    # it when there's no Link at all.
    n["_material_name"] = link or n.get("MaterialName")


def _material_user_inst_001(r, n):
    version = r.i32()
    _noderef(r)  # CPlugBitmapAtlas
    if version == 2:
        raise ValueError("CPlugMaterialUserInst chunk 001 version 2 not supported")
    if version >= 3:
        r.i32()  # TilingU
        r.i32()  # TilingV
        r.f32()  # TextureSizeInMeters
        if version >= 4:
            r.i32()  # int? -- "?" is a C#-side nullable type annotation
                     # here, not a separate wire-level presence flag; its
                     # actual presence is already gated by "version >= 4".
            if version >= 5:
                r.bool()  # IsNatural


def _material_user_inst_002(r, n):
    r.i32()  # version
    r.i32()


_register(0x090FD000, {
    0x090FD000: (False, _material_user_inst_000),
    0x090FD001: (False, _material_user_inst_001),
    0x090FD002: (False, _material_user_inst_002),
})


def _read_node_direct(r, class_id):
    """Read a node embedded directly inline (no index/class-id prefix --
    GBX.NET's ReadNode<T>, used where the containing type is statically
    known, e.g. CPlugVisualIndexed's IndexBuffer)."""
    node = {"_class": class_id, "_class_hex": f"0x{class_id:08X}"}
    parser = _NODE_PARSERS.get(class_id)
    _read_node_body(r, node, _NODE_PARSERS, parser)
    return node


# --- CPlugIndexBuffer 0x09057000 ----------------------------------------

def _index_buffer_000(r, n):
    n["Flags"] = r.i32()
    count = r.i32()
    n["Indices"] = [r.u16() for _ in range(count)]


def _index_buffer_001(r, n):
    # Same as 0x000 but delta-encoded (int16 differences).
    n["Flags"] = r.i32()
    count = r.i32()
    indices = []
    current = 0
    for _ in range(count):
        current += struct.unpack_from("<h", r.bytes(2))[0]
        indices.append(current)
    n["Indices"] = indices


_register(0x09057000, {
    0x09057000: (False, _index_buffer_000),
    0x09057001: (False, _index_buffer_001),
})


# --- CPlugVertexStream 0x09056000 ---------------------------------------
# EPlugVDclType
_VDCL_TYPE_U01, _VDCL_TYPE_FLOAT2, _VDCL_TYPE_FLOAT3, _VDCL_TYPE_FLOAT4, \
    _VDCL_TYPE_COLOR, _VDCL_TYPE_INT32 = range(6)
_VDCL_TYPE_DEC3N = 14
# EPlugVDcl
_VDCL_POSITION, _VDCL_POSITION1, _VDCL_TGT_ROTATION, _VDCL_BLEND_WEIGHT, \
    _VDCL_BLEND_INDICES, _VDCL_NORMAL, _VDCL_NORMAL1, _VDCL_POINT_SIZE, \
    _VDCL_COLOR0, _VDCL_COLOR1, _VDCL_TEXCOORD0 = range(11)
_VDCL_TEXCOORD7 = _VDCL_TEXCOORD0 + 7
_VDCL_TANGENTU = 18
_VDCL_TANGENTV = 20


def _vec3_10b(r):
    val = r.i32()
    x = val & 0x3FF
    y = (val >> 10) & 0x3FF
    z = (val >> 20) & 0x3FF
    if x & 0x200:
        x -= 0x400
    if y & 0x200:
        y -= 0x400
    if z & 0x200:
        z -= 0x400
    return (x / 511.0, y / 511.0, z / 511.0)


def _read_data_decl(r, composite_version):
    version = composite_version & 7
    count = composite_version >> 3

    flags1 = r.u32()
    flags2 = r.u32()
    weight_count = flags1 & 0x1FF
    vdcl_type = (flags1 >> 9) & 0x1FF

    if (flags2 & 0xFFC) == 0:
        if version == 0:
            data_len = ((flags1 >> 0x12) & 0x3FF) * count
            r.bytes(data_len)
    else:
        r.u16()  # u02
        offset = r.u16()
        if ((flags2 >> 2) & 0x3FF) != offset:
            raise ValueError("DataDecl offset mismatch")

    return {"Type": vdcl_type, "WeightCount": weight_count}


def _vertex_stream_000(r, n):
    version = r.i32()
    count = r.i32()
    r.u32()  # flags (DoData)
    stream_model = _noderef(r)

    if count == 0 or stream_model is not None:
        return

    decl_count = r.i32()
    composite_version = version | (count << 3)
    decls = [_read_data_decl(r, composite_version) for _ in range(decl_count)]

    if version == 0:
        return

    r.bool()  # U01

    positions = None
    uvs = {}
    normals = None
    colors = {}

    for decl in decls:
        t = decl["Type"]
        wc = decl["WeightCount"]
        if t == _VDCL_TYPE_FLOAT2:
            if _VDCL_TEXCOORD0 <= wc <= _VDCL_TEXCOORD7:
                uvs[wc - _VDCL_TEXCOORD0] = [r.vec2() for _ in range(count)]
            elif wc == _VDCL_BLEND_WEIGHT:
                [r.vec2() for _ in range(count)]
            else:
                raise ValueError(f"unknown Float2 vertex decl {wc}")
        elif t == _VDCL_TYPE_FLOAT3:
            if wc == _VDCL_POSITION:
                positions = r.array_vec3(count)
            elif wc == _VDCL_POSITION1:
                r.array_vec3(count)
            elif wc == _VDCL_NORMAL:
                normals = [_vec3_10b(r) for _ in range(count)]
            elif wc == _VDCL_NORMAL1:
                [_vec3_10b(r) for _ in range(count)]
            else:
                raise ValueError(f"unknown Float3 vertex decl {wc}")
        elif t == _VDCL_TYPE_FLOAT4:
            raise ValueError(f"unknown Float4 vertex decl {wc}")
        elif t == _VDCL_TYPE_COLOR:
            if _VDCL_COLOR0 <= wc <= _VDCL_COLOR0 + 2:
                colors[wc - _VDCL_COLOR0] = r.array_i32(count)
            else:
                raise ValueError(f"unknown Color vertex decl {wc}")
        elif t == _VDCL_TYPE_INT32:
            if wc == _VDCL_BLEND_INDICES:
                r.array_i32(count)
            else:
                raise ValueError(f"unknown Int32 vertex decl {wc}")
        elif t == _VDCL_TYPE_DEC3N:
            if wc == _VDCL_NORMAL:
                normals = [_vec3_10b(r) for _ in range(count)]
            elif wc == _VDCL_TANGENTU:
                [_vec3_10b(r) for _ in range(count)]
            elif wc == _VDCL_TANGENTV:
                [_vec3_10b(r) for _ in range(count)]
            else:
                raise ValueError(f"unknown Dec3N vertex decl {wc}")
        else:
            raise ValueError(f"unsupported vertex decl type {t}")

    n["Positions"] = positions
    n["UVs"] = uvs
    n["Normals"] = normals
    n["Colors"] = colors


_register(0x09056000, {
    0x09056000: (False, _vertex_stream_000),
})


# --- CPlugVisual 0x09006000 / CPlugVisual3D 0x0902C000 /
#     CPlugVisualIndexed 0x0906A000 / CPlugVisualIndexedTriangles
#     0x0901E000 -- hand-ported from GBX.NET's own CPlugVisual.cs,
#     CPlugVisual3D.cs, CPlugVisualIndexed.cs, CPlugIndexBuffer.cs (the
#     .chunkl schema for this whole class family is stale/empty; these
#     hand-written readers are what's actually authoritative). ---------

def _visual_001(r, n):
    n["_001_id"] = r.read_id_as_string()


def _visual_004(r, n):
    n["_004"] = _noderef(r)


def _visual_005(r, n):
    count = r.i32()
    n["SubVisuals"] = [(r.i32(), r.i32(), r.i32()) for _ in range(count)]


def _visual_009(r, n):
    r.f32()


def _visual_00B(r, n):
    count = r.i32()
    # archive Split: int; int; box BoundingBox -- always empty in every
    # file seen so far, so the exact "box" layout (vs "boxaligned") has
    # never been exercised; best-effort guess if it ever isn't empty.
    n["Splits"] = [(r.i32(), r.i32(), r.box_aligned()) for _ in range(count)]


def _visual_010(r, n):
    r.i32()  # version
    morph_count = r.i32()
    if morph_count > 0:
        raise ValueError("CPlugVisual morph targets are not supported")


def _convert_chunk_flags_to_flags(chunk_flags):
    flags = 0
    flags |= chunk_flags & 15
    flags |= (chunk_flags << 1) & 0x20
    flags |= (chunk_flags << 2) & 0x80
    flags |= (chunk_flags << 2) & 0x100
    flags |= (chunk_flags << 13) & 0x100000
    flags |= (chunk_flags << 13) & 0x200000
    flags |= (chunk_flags << 13) & 0x400000
    return flags


def _read_tex_coord_set(r, expected_count):
    version = r.i32()
    flags = None
    if version >= 3:
        actual_count = r.i32()
        if actual_count != expected_count:
            raise ValueError("TexCoord actualCount != expectedCount")
        flags = r.i32()
        if (flags & 0xFF) > 2:
            raise ValueError("TexCoord flags kind > 2")

    tex_coords = []
    for _ in range(expected_count):
        uv = r.vec2()
        if 1 <= version < 3:
            r.i32()
            if version >= 2:
                r.i32()
        tex_coords.append(uv)

    if version >= 3 and flags is not None:
        r.array_f32((expected_count * flags) & 0xFF)

    return tex_coords


def _read_bitmap_elem_to_pack(r):
    return (r.i32(), r.i32(), r.i32(), r.i32(), r.i32())


def _read_skin_data(r, v):
    # version/count packed the same way as DataDecl's composite version.
    version = v & 15
    r.bool()  # U01
    r.i32()  # U02
    u03 = False
    if version >= 5:
        u03 = r.bool()
        r.bool()  # U04
    if u03:
        raise ValueError("CPlugVisual SkinData U03 is true (not supported)")
    bone_count = r.i32()
    if version == 2:
        r.array_readable(lambda rr: rr.iso4())  # U05: Iso4[]
    for _ in range(bone_count):
        r.read_id_as_string()  # Bones
    if version != 3:
        r.array_i32()  # U07


def _visual_00F(r, n):
    version = r.i32()
    n["Flags"] = flags = _convert_chunk_flags_to_flags(r.i32())
    num_tex_coord_sets = r.i32()
    n["Count"] = count = r.i32()
    n["VertexStreams"] = _array_noderef(r)

    n["TexCoords"] = [_read_tex_coord_set(r, count) for _ in range(num_tex_coord_sets)]

    if (flags & 7) != 0:
        _read_skin_data(r, (2 + version) | ((flags & 7) << 4))

    n["BoundingBox"] = r.box_aligned()
    n["BitmapElemToPacks"] = r.array_readable(_read_bitmap_elem_to_pack)

    if version >= 5:
        uv_group_count = r.i32()
        n["UvGroups"] = [r.u16() for _ in range(uv_group_count)]
        if version >= 6:
            r.i32()  # U02
            u03 = r.i32()
            if u03 > 0:
                r.bytes(u03 - 4)  # U04


def _visual_006(r, n):
    if r.bool():  # HasVertexNormals
        n["Flags"] = n.get("Flags", 0) | (1 << 7)


def _read_visual_00D_body(r, n, skin_version):
    n["Flags"] = flags = _convert_chunk_flags_to_flags(r.i32())
    num_tex_coord_sets = r.i32()
    n["Count"] = count = r.i32()
    n["VertexStreams"] = _array_noderef(r)

    n["TexCoords"] = [_read_tex_coord_set(r, count) for _ in range(num_tex_coord_sets)]

    if (flags & 7) != 0:
        _read_skin_data(r, skin_version | ((flags & 7) << 4))

    n["BoundingBox"] = r.box_aligned()


def _visual_00D(r, n):
    _read_visual_00D_body(r, n, 1)


def _visual_00E(r, n):
    # TMNF/TMUF visuals: 0x00D + BitmapElemToPacks.
    _read_visual_00D_body(r, n, 2)
    n["BitmapElemToPacks"] = r.array_readable(_read_bitmap_elem_to_pack)


_register(0x09006000, {
    0x09006001: (False, _visual_001),
    0x09006004: (False, _visual_004),
    0x09006005: (False, _visual_005),
    0x09006006: (False, _visual_006),
    0x09006009: (False, _visual_009),
    0x0900600B: (False, _visual_00B),
    0x0900600D: (False, _visual_00D),
    0x0900600E: (False, _visual_00E),
    0x0900600F: (False, _visual_00F),
    0x09006010: (False, _visual_010),
})


# --- CPlugVisual3D 0x0902C000 (inherits CPlugVisual) --------------------

def _visual3d_002(r, n):
    n["_002"] = _noderef(r)


def _visual3d_004(r, n):
    flags = n.get("Flags", 0)
    has_vertex_normals = bool(flags & (1 << 7))
    u01 = (not (flags & (1 << 22))) or has_vertex_normals
    u02 = (not (flags & (1 << 22))) or bool(flags & (1 << 8))
    u03 = bool(flags & (1 << 20))
    u04 = bool(flags & (1 << 21))

    is_sprite = n.get("_class") == 0x09010000  # CPlugVisualSprite

    if not n.get("VertexStreams"):
        count = n.get("Count", 0)
        vertices = []
        normals = []
        colors = []
        for _ in range(count):
            pos = r.vec3()
            if u01:
                if u03:
                    normals.append(_vec3_10b(r))  # packed normal
                else:
                    normals.append(r.vec3())
            if u02:
                if u04:
                    r.i32()  # packed color
                else:
                    colors.append((r.f32(), r.f32(), r.f32(), r.f32()))  # Vec4 color
            if is_sprite:
                r.f32()  # U08
                r.i32()  # U09
            vertices.append(pos)
        n["Vertices"] = vertices
        n["Normals"] = normals
        n["Colors"] = colors

    num_bytes_per_tangent = ((~((flags >> 17) & 0xFF)) & 8) | 4

    def read_tangents():
        num_elems = r.i32()
        if num_elems != 0:
            r.bytes(num_elems * num_bytes_per_tangent)

    read_tangents()
    read_tangents()


_register(0x0902C000, {
    0x0902C002: (False, _visual3d_002),
    0x0902C004: (False, _visual3d_004),
}, bases=(0x09006000,))


# --- CPlugVisualIndexed 0x0906A000 (inherits CPlugVisual3D) -------------

def _visual_indexed_000(r, n):
    count = r.i32()
    n["IndexBuffer"] = {"Indices": [r.u16() for _ in range(count)]}


def _visual_indexed_001(r, n):
    if r.bool():
        n["IndexBuffer"] = _read_node_direct(r, 0x09057000)


_register(0x0906A000, {
    0x0906A000: (False, _visual_indexed_000),
    0x0906A001: (False, _visual_indexed_001),
}, bases=(0x0902C000,))


# --- CPlugVisualIndexedTriangles 0x0901E000 (inherits CPlugVisualIndexed,
#     no chunks of its own) ------------------------------------------

_register(0x0901E000, {}, bases=(0x0906A000,))


# --- CPlugVisualSprite 0x09010000 (inherits CPlugVisual3D) / CPlugSpriteParam
#     0x090AC000 -- from GBX.NET's .chunkl schemas. Camera-facing billboards
#     (e.g. TMNF clouds): parsed to get past them, not turned into a mesh. -

def _visual_sprite_005(r, n):
    r.i32()
    for _ in range(5):
        r.f32()


def _visual_sprite_006(r, n):
    r.u16()
    r.u16()


def _visual_sprite_008(r, n):
    n["SpriteParam"] = _read_node_direct(r, 0x090AC000)


def _visual_sprite_009(r, n):
    count = r.i32()
    for _ in range(count):
        r.f32(); r.f32(); r.f32(); r.f32()  # Rect


_register(0x09010000, {
    0x09010005: (False, _visual_sprite_005),
    0x09010006: (False, _visual_sprite_006),
    0x09010008: (False, _visual_sprite_008),
    0x09010009: (False, _visual_sprite_009),
}, bases=(0x0902C000,))


def _read_sprite_param_000_body(r):
    r.u32()
    r.vec3()  # GlobalDirection
    r.vec2()  # PivotPoint
    r.f32()  # GlobalDirTiltFactor


def _sprite_param_000(r, n):
    _read_sprite_param_000_body(r)


def _sprite_param_001(r, n):
    version = r.i32()
    _read_sprite_param_000_body(r)
    r.f32()  # TextureHeightInWorld
    if version >= 1:
        r.f32()  # VisibleMaxDistAtFov90
        r.f32()  # VisibleMinScreenHeight01


_register(0x090AC000, {
    0x090AC000: (False, _sprite_param_000),
    0x090AC001: (False, _sprite_param_001),
})


class _UnsupportedItemMesh(RuntimeError):
    """Raised as soon as we discover the item uses a mesh format this
    pure-Python parser doesn't implement (Prefab / legacy CPlugSolid),
    instead of failing deep inside a recursive parse with a confusing
    low-level byte-alignment error."""


def _unsupported_class(class_name):
    def _raise(r, n):
        raise _UnsupportedItemMesh(
            f"This item's mesh uses {class_name}, a format this "
            f"pure-Python importer doesn't support yet."
        )
    return _raise


# Legacy (pre-StaticObject) VisModel-path support classes whose own full
# binary layout isn't implemented -- registered as "unsupported" stubs so
# that IF they're ever actually non-null, the user gets a clear message
# instead of a raw "no parser registered" crash. They're not expected to
# be populated for plain static architecture items (only for physics/
# gameplay entities), which is what this path is for.
_register(0x090F8000, {0x090F8000: (False, _unsupported_class("CPlugAnimLocSimple"))})  # CPlugAnimLocSimple
_register(0x090B0000, {0x090B0000: (False, _unsupported_class("CPlugAnimFile"))})       # CPlugAnimFile

# CPlugMaterial: only reachable if a CPlugSurface.SurfMaterial actually
# embeds a full material NodeRef instead of a plain SurfaceId enum
# (uncommon in practice) -- not implemented.
def _material_007(r, n):
    n["Custom"] = _noderef(r)  # CPlugMaterialCustom


def _material_00D(r, n):
    n["Base"] = _noderef(r)  # external .Material.Gbx


_register(0x09079000, {
    0x09079000: (False, _unsupported_class("CPlugMaterial")),
    # Written by tmunlimiter_blender_plugin (object_texture/texture_custom.py)
    0x09079007: (False, _material_007),
    0x0907900D: (False, _material_00D),
})


# --- CPlugSurface 0x0900C000 -- hand-ported from GBX.NET's own
#     CPlugSurface.cs reader (collision shapes: Sphere/Ellipsoid/Box/
#     Mesh/Compound). Reached via CGameObjectPhyModel's Move/Hit/Trigger
#     ShapeFid or CPlugStaticObjectModel.Shape when the corresponding
#     string ref is empty. -------------------------------------------

def _read_vec4(r):
    return (r.f32(), r.f32(), r.f32(), r.f32())


def _read_int3(r):
    return (r.i32(), r.i32(), r.i32())


def _read_cooked_triangle(r):
    return (_read_vec4(r), _read_int3(r), r.u16(), r.u8(), r.u8())


def _read_octree_cell(r):
    return (r.i32(), r.vec3(), r.vec3(), r.i32())


def _read_mesh_triangle(r):
    return (_read_int3(r), r.u8(), r.u8(), r.u16())


def _read_aabb_tree_cell(r):
    return (r.vec3(), r.vec3(), r.i32())


def _read_surf(r, version):
    """Read one collision shape; returns it as a dict (only Mesh/Box/Compound
    keep their geometry, used to import TMNF triggers/collision), or None."""
    surf_id = r.i32()
    if surf_id == -1:  # no surf
        return None
    surf = {"Type": surf_id}
    if surf_id == 0:  # Sphere
        r.f32()  # Size
        if version >= 1:
            r.u16()  # SurfaceIndex
    elif surf_id == 1:  # Ellipsoid
        r.vec3()  # Size
        if version >= 1:
            r.u16()  # SurfaceIndex
    elif surf_id == 6:  # Box
        surf["Box"] = r.box_aligned()  # Transform (center xyz, half-size xyz)
        if version >= 1:
            r.u16()  # SurfaceIndex
    elif surf_id == 7:  # Mesh
        mesh_version = r.i32()
        if mesh_version in (1, 2, 3):
            surf["Vertices"] = r.array_vec3()
            cooked = r.array_readable(_read_cooked_triangle)  # CookedTriangles
            surf["Triangles"] = [t[1] for t in cooked]
            surf["TriangleMaterials"] = [t[2] for t in cooked]  # index into the CPlugSurface's Materials
            octree_version = r.i32()
            if octree_version == 0 and r.pos + 6 <= len(r.data) and                     struct.unpack_from("<I", r.data, r.pos + 2)[0] == _FACADE:
                # tmunlimiter_blender_plugin (plug_surface.py) writes just this
                # one 0 (no octree list), then the geom's u16 SurfaceId.
                pass
            elif octree_version == 1:
                r.i32()  # deprec version marker
                r.array_readable(_read_octree_cell)  # OctreeCells
            else:
                r.array_readable(_read_octree_cell)
        elif mesh_version == 5:
            surf["Vertices"] = r.array_vec3()
            surf["Triangles"] = [t[1] for t in r.array_readable(_read_cooked_triangle)]  # CookedTriangles
            r.i32()
            r.array_readable(_read_aabb_tree_cell)  # AABBTreeCells
        elif mesh_version in (6, 7):
            surf["Vertices"] = r.array_vec3()
            surf["Triangles"] = [t[0] for t in r.array_readable(_read_mesh_triangle)]  # Triangles
    elif surf_id == 13:  # Compound
        surf_count = r.i32()
        surf["Surfs"] = [_read_surf(r, version) for _ in range(surf_count)]
        surf["SurfLocs"] = [r.iso4() for _ in range(surf_count)]
        if version >= 1:
            joint_count = r.i32()
            for _ in range(joint_count):
                r.u16()  # SurfJoints
    else:
        raise ValueError(f"unknown CPlugSurface surf type {surf_id}")

    if version >= 2:
        r.vec3()  # GameplayMainDir
    return surf


def _read_surf_material(r):
    has_material = r.bool()
    if has_material:
        return {"Material": _noderef(r)}  # CPlugMaterial (TMNF: external .Material.Gbx)
    return {"SurfaceId": r.u16()}  # MaterialId enum


def _surface_003(r, n):
    version = r.i32()
    surf_version = 0
    if version >= 2:
        surf_version = r.i32()
    _read_surf(r, surf_version)
    n["Materials"] = r.array_readable(_read_surf_material)

    if (version == 3 and not n["Materials"]) or version > 3:
        r.i32()  # U05

    if version < 3:
        length = r.i32()
        r.bytes(length)  # U01 (Data)
    else:
        count = r.i32()
        for _ in range(count):
            r.u16()  # U02

    if version >= 1:
        n["Skel"] = _noderef(r)

    if version >= 5:
        id_count = r.i32()
        for _ in range(id_count):
            r.read_id_as_string()  # U06


def _surface_000(r, n):
    # TMNF/TMUF: geometry in a separate CPlugSurfaceGeom node.
    n["Geom"] = _noderef(r)
    n["Materials"] = r.array_readable(_read_surf_material)


_register(0x0900C000, {
    0x0900C000: (False, _surface_000),
    0x0900C003: (False, _surface_003),
})


# --- CPlugSurfaceGeom 0x0900F000 -- hand-ported from GBX.NET's own
#     CPlugSurfaceGeom.cs (TMNF/TMUF collision geometry). --------------

def _surface_geom_002(r, n):
    n["Surf"] = _read_surf(r, 0)
    r.u16()  # SurfaceId


def _surface_geom_004(r, n):
    r.read_id_as_string()
    r.box_aligned()
    n["Surf"] = _read_surf(r, 0)
    r.u16()  # SurfaceId


_register(0x0900F000, {
    0x0900F002: (False, _surface_geom_002),
    0x0900F004: (False, _surface_geom_004),
})


def _read_trigger_action_archive(r, version):
    raise _UnsupportedItemMesh("This item uses CPlugTriggerAction data, which isn't supported yet.")


# --- CPlugSkel 0x090BA000 -- hand-ported from GBX.NET's own CPlugSkel.cs
#     reader (its .chunkl schema is stale/empty). Not needed for mesh
#     geometry, but CPlugSolid2Model.Skel must still be parsed correctly
#     (when non-null) to stay byte-aligned for the fields after it. ------

def _read_data_blob(r):
    length = r.i32()
    return r.bytes(length)


def _read_joint_archive(r, version):
    name = r.read_id_as_string()
    parent_index = r.u16()
    if version <= 13:
        r.f32(); r.f32(); r.f32(); r.f32()  # quat GlobalJoint
        r.vec3()
    if version >= 1:
        r.iso4()
    return {"Name": name, "ParentIndex": parent_index}


def _read_socket_archive(r, version):
    name = r.read_id_as_string()
    r.u16()
    r.iso4()
    return {"Name": name}


def _skel_000(r, n):
    version = r.i32()
    n["Name"] = r.read_id_as_string()
    joints_length = r.u16()
    n["Joints"] = [_read_joint_archive(r, version) for _ in range(joints_length)]

    if version < 2:
        return
    if r.bool():
        raise ValueError("CPlugSkel u01 == true (unsupported)")

    if version < 6:
        return
    n["Sockets"] = r.array_readable(_read_socket_archive, version=version)

    if version < 9:
        return
    if r.bool():
        raise ValueError("CPlugSkel u02 == true (unsupported)")

    if version < 10:
        return
    if version >= 16:
        _read_data_blob(r)  # u04
        if version >= 18:
            _read_data_blob(r)  # second u04
    else:
        r.array_i32()  # u03

    if version >= 13:
        if version < 16:
            _read_data_blob(r)  # u04
        if version == 14:
            r.i32()  # literal 0 marker
            r.i32()  # JointExpr[] count (JointExpr itself has zero fields)
        if version >= 19:
            _read_data_blob(r)  # u07

    if version >= 17:
        if version >= 20:
            r.array_vec3()  # u08
        r.u8()  # u05
        r.i32()  # u06


_register(0x090BA000, {
    0x090BA000: (False, _skel_000),
})


# --- CPlugLightUserModel 0x090F9000 -------------------------------------

def _light_user_model_000(r, n):
    version = r.i32()
    r.i32()
    n["Color"] = r.vec3()
    n["Intensity"] = r.f32()
    n["Distance"] = r.f32()
    r.f32()  # PointEmissionRadius
    r.f32()  # PointEmissionLength
    r.f32()  # SpotInnerAngle
    r.f32()  # SpotOuterAngle
    r.f32()  # SpotEmissionSizeX
    r.f32()  # SpotEmissionSizeY
    if version >= 1:
        r.bool()  # NightOnly


_register(0x090F9000, {
    0x090F9000: (False, _light_user_model_000),
})


# --- CGameObjectPhyModel 0x2E006000 -- hand-ported from GBX.NET's own
#     CGameObjectPhyModel.cs reader (physics-only data; not needed for
#     mesh geometry itself, but must be parsed correctly to stay in sync
#     since it precedes VisModel in the legacy pre-StaticObject format). -

def _phy_model_001(r, n):
    version = r.i32()

    if version < 11:
        n["MoveShapeFid"] = _noderef(r)
        n["HitShapeFid"] = _noderef(r)
        n["TriggerShapeFid"] = _noderef(r)

    trigger_action_version = r.i32() if version >= 8 else 5

    trigger_count = r.i32()
    if trigger_count > 0:
        _read_trigger_action_archive(r, trigger_action_version)

    if version < 14:
        _noderef(r)  # U03

    if version < 2:
        return
    n["MoveShape"] = move_shape = r.string()

    if version >= 4:
        n["HitShape"] = hit_shape = r.string()
    else:
        hit_shape = None

    if version < 3:
        return
    if r.bool():
        raise _UnsupportedItemMesh("This item uses a CPlugDynaPointModel, which isn't supported yet.")

    if version < 5:
        return
    r.i32()  # Program enum

    if version < 6:
        return
    if version >= 22:
        if r.bool_byte():
            r.iso4()
    else:
        r.iso4()

    if version < 7:
        return
    n["TriggerShape"] = trigger_shape = r.string()

    if version < 9:
        return
    action_model = r.string() if version >= 13 else None
    if not action_model:
        _array_noderef(r)  # Actions

    if version >= 21:
        _noderef(r)  # U01

    if version < 11:
        return
    if not move_shape:
        n["MoveShapeFid"] = _noderef(r)
    if not hit_shape:
        n["HitShapeFid"] = _noderef(r)
    if not trigger_shape:
        n["TriggerShapeFid"] = _noderef(r)

    if version < 12:
        return
    u14 = r.string()
    if not u14:
        _noderef(r)  # U15

    if version < 15:
        return
    r.i32()  # U19

    if version < 16:
        return
    n["SpecialProperties"] = _noderef(r)

    if version < 17:
        return
    r.i32()  # Persistence enum

    if version < 18:
        return
    r.bool()  # canStopEnemy
    r.bool()  # canStopEnemyBullet

    if version < 19:
        return
    r.f32()  # throwSpeed
    r.f32()  # throwAngularSpeed
    r.i32()  # armor
    r.bool()  # hasALifeTime
    r.i32()  # lifeTimeDuration
    r.f32()  # scaleCoefMax
    r.f32()  # staminaSpawnCoef
    r.i32()  # timeBeforeDome
    r.bool(); r.bool(); r.bool(); r.bool(); r.bool()  # U20..U24
    r.bool()  # healEnabled
    r.i32()   # healArmorGainPerSecond
    r.bool()  # shieldEnabled
    r.i32()   # shieldDomeArmor

    if version < 20:
        return
    r.bool()  # U25

    if version < 23:
        return
    r.bool()  # bumperEnabled

    if version < 24:
        return
    r.bool()  # magnetEnabled

    if version < 25:
        return
    _noderef(r)  # U26


def _phy_model_003(r, n):
    if r.bool():
        raise ValueError("CGameObjectPhyModel chunk 003 flag is true (unsupported)")


_register(0x2E006000, {
    0x2E006001: (False, _phy_model_001),
    0x2E006003: (False, _phy_model_003),
})


# --- CGameObjectVisModel 0x2E007000 -- hand-ported from GBX.NET's own
#     CGameObjectVisModel.cs reader (the legacy pre-StaticObject mesh
#     path: MeshShaded is a CPlugSolid2Model NodeRef, Mesh is a plain
#     filename string referencing a sibling .Mesh.Gbx file, Solid is the
#     even-older CPlugSolid/CPlugTree hierarchy). -----------------------

def _vis_model_001(r, n):
    version = r.i32()

    if version < 9:
        _noderef(r)  # U14
    else:
        n["Mesh"] = r.string()
        if not n["Mesh"]:
            n["MeshShaded"] = _noderef(r)

    if version < 18:
        _noderef(r)  # U16 (CPlugAnimFile)

    if version >= 2:
        if version < 9:
            n["Mesh"] = r.string()
        n["LocAnim"] = _noderef(r)
        r.i32()  # SPlugLightBallStateSimple array marker

    if version < 17:
        r.string()  # SoundRefSpawn
        r.string()  # SoundRefUnspawn
        r.string()  # SoundRefGrab

    if version < 10:
        return
    u07 = r.string()
    if version >= 11 and u07:
        r.f32(); r.f32(); r.f32()  # U18..U20

    if version < 12:
        return
    n["SmashParticleRef"] = smash_particle_ref = r.string()
    if smash_particle_ref:
        r.read_id_as_string()  # U21

    if version < 13:
        return
    r.i32()  # CPlugFileImg array marker
    r.i32()  # SSpriteParam array marker

    if version < 14:
        return
    n["SolidRef"] = solid_ref = r.string()
    if not solid_ref:
        n["Solid"] = _noderef(r)

    if version < 16:
        return
    _noderef(r)  # U10 (CPlugParticleEmitterModel)

    if version < 19:
        return
    r.f32()  # U12

    if version < 20:
        return
    n["VisEntFx"] = vis_ent_fx = r.string()
    if not vis_ent_fx:
        _noderef(r)  # U13

    if version < 21:
        return
    n["MeshShadedFid"] = _noderef(r)

    if version < 22:
        return
    r.vec3()  # DomeShaderColor


_register(0x2E007000, {
    0x2E007001: (False, _vis_model_001),
})


# --- CPlugSolid2Model 0x090BB000 -- hand-ported from GBX.NET's own
#     CPlugSolid2Model.cs reader (its .chunkl schema is stale/empty). ----

def _read_shaded_geom_archive(r, version):
    g = {}
    g["VisualIndex"] = r.i32()
    g["MaterialIndex"] = r.i32()
    r.i32()  # unused (always -1 in practice)
    if version >= 1:
        g["LodMask"] = r.i32()
        if version >= 32:
            r.i32()
    return g


def _read_prelightgen_archive(r):
    version = r.i32()
    r.i32()
    r.f32()
    r.bool()
    for _ in range(8):
        r.f32()
    r.i32()
    r.i32()  # int2 SpriteCount
    r.array_readable(lambda rr: rr.box_aligned())  # boxaligned[]
    if version >= 1:
        count = r.i32()
        for _ in range(count):
            r.i32(); r.i32(); r.i32(); r.i32()  # int4[] UvGroups


def _read_light_archive(r, version):
    light = {"U01": r.read_id_as_string()}
    u02 = r.bool()
    if u02:
        _noderef(r)  # U03 CPlugLight (external)
    else:
        r.string()  # U04
    r.iso4()  # U05
    for _ in range(6):
        r.i32()  # U06..U11
    if version >= 26:
        r.i32(); r.i32(); r.i32()  # U12..U14
    if r.bool():  # U15
        r.f32(); r.f32(); r.f32()  # U16..U18
    return light


def _read_light_inst_archive(r):
    return {"ModelIndex": r.i32(), "SocketIndex": r.i32()}


def _solid2model_000(r, n):
    version = r.i32()
    r.read_id_as_string()  # U01

    n["ShadedGeoms"] = r.array_readable(_read_shaded_geom_archive, version=version)

    visuals = []
    if version >= 6:
        r.i32()  # deprec version marker
        visuals = _array_noderef(r)
    n["Visuals"] = visuals

    material_id_count = r.i32()
    n["MaterialIds"] = [r.read_id_as_string() for _ in range(material_id_count)]

    material_count = r.i32() if version >= 29 else 0

    materials = []
    if material_count == 0:
        r.i32()  # deprec version marker
        materials = _array_noderef(r)
    n["Materials"] = materials

    n["Skel"] = _noderef(r)

    custom_materials = []

    if version >= 1:
        n["LodMaxDistAtFov90"] = r.array_f32()
        if version >= 2:
            n["VisCstType"] = r.i32()
            if version >= 3:
                pre_light = r.bool()
                if pre_light:
                    _read_prelightgen_archive(r)
                if version >= 4:
                    r.bytes(8)  # FileWriteTime
                    if version >= 5:
                        r.string()  # U03
                        if version >= 7:
                            n["MaterialsFolderName"] = r.string()
                            if version >= 19:
                                r.string()  # U04 (shader?)
                            if version >= 8:
                                n["Lights"] = r.array_readable(_read_light_archive, version=version)
                                if version < 16:
                                    n["MaterialInsts"] = _array_noderef(r)
                                if version >= 10:
                                    n["LightUserModels"] = _array_noderef(r)
                                    n["LightInsts"] = r.array_readable(_read_light_inst_archive)
                                    if version >= 11:
                                        r.i32()  # DamageZone
                                        if version >= 12:
                                            r.u32()  # flags (DoData)
                                            if version >= 13:
                                                r.i32()  # U05
                                                if version >= 14:
                                                    r.string()  # U06
                                                    if version >= 15:
                                                        if version < 29:
                                                            material_count = r.i32()
                                                        if version >= 30:
                                                            r.i32()  # U07
                                                        custom_materials = r.array_readable(
                                                            _read_material_archive, count=material_count)
                                                        if version >= 17:
                                                            if version < 21:
                                                                r.array_readable(lambda rr: rr.box_aligned())
                                                            if version >= 20:
                                                                joint_count = r.i32()
                                                                for _ in range(joint_count):
                                                                    r.read_id_as_string()
                                                                if version >= 22:
                                                                    r.array_i32()  # U10
                                                                    if version >= 23:
                                                                        u11 = r.i32()
                                                                        if u11 > 0:
                                                                            raise ValueError("Solid2Model U11 > 0 not supported")
                                                                        r.array_i32()  # U12
                                                                        if version >= 24:
                                                                            r.i32()  # U13
                                                                            if version >= 25:
                                                                                _noderef(r)  # U14
                                                                                r.f32()  # U15
                                                                                r.f32()  # U16
                                                                                if version >= 27:
                                                                                    r.read_id_as_string()  # U17
                                                                                    if version >= 31:
                                                                                        u18 = r.i32()
                                                                                        if u18 > 0:
                                                                                            raise ValueError("Solid2Model U18 > 0 not supported")
                                                                                        if version >= 33:
                                                                                            if version < 34:
                                                                                                r.i32()
                                                                                            count19 = r.i32()
                                                                                            for _ in range(count19):
                                                                                                r.i32(); r.i32(); r.i32(); r.i32(); r.i32()

    n["CustomMaterials"] = custom_materials


_register(0x090BB000, {
    0x090BB000: (False, _solid2model_000),
})


def _solid2_material_name(solid2_node, material_index):
    """Mirror BlenderGbxTools' ShadedGeom.GetMaterialName() priority
    order: Materials, then MaterialInsts, then CustomMaterials, then
    MaterialIds."""
    material_insts = solid2_node.get("MaterialInsts") or []
    if material_index < len(material_insts) and material_insts[material_index]:
        return _clean_material_name(material_insts[material_index].get("_material_name"))

    custom_materials = solid2_node.get("CustomMaterials") or []
    if material_index < len(custom_materials):
        return _material_display_name(custom_materials[material_index])

    material_ids = solid2_node.get("MaterialIds") or []
    if material_index < len(material_ids):
        return _clean_material_name(material_ids[material_index])

    return None


# --- CGameCommonItemEntityModel 0x2E027000 -------------------------------

def _common_item_entity_model_000(r, n):
    version = r.i32()
    if version == 0:
        n["PhyModel"] = _noderef(r)
        n["VisModel"] = _noderef(r)
    if version == 3:
        r.string()
        r.string()
    if version >= 4:
        n["StaticObject"] = _noderef(r)
    if version >= 2:
        n["TriggerShape"] = _noderef(r)
        r.iso4()
        _noderef(r)  # CPlugParticleEmitterModel
        n["Actions"] = _array_noderef(r)
        if version <= 5:
            _noderef(r)
        r.string()
        r.string()
        r.string()
        r.string()
        r.string()
        r.iso4()
        r.i32()  # ExprValidator
        if version >= 5:
            r.u8()


_register(0x2E027000, {
    0x2E027000: (False, _common_item_entity_model_000),
})

# CGameBlockItem 0x2E025000: Block-type items store their Crystal under
# CustomizedVariants[], a different layout than the Ornament-type
# EntityModelEdition.MeshCrystal path this parser implements.
_register(0x2E025000, {
    0x2E025000: (False, _unsupported_class("CGameBlockItem (block-type item)")),
})

# CPlugPrefab 0x09145000: an item made of nested sub-items ("Ents"),
# recursively combining meshes -- not implemented.
_register(0x09145000, {
    0x09145000: (False, _unsupported_class("CPlugPrefab (composite item)")),
})


# --- CPlugSolid 0x09005000 / CPlugTree 0x0904F000 -- TMNF/TMUF .Solid.Gbx
#     meshes, hand-ported from GBX.NET's CPlugSolid.chunkl, CPlugTree.cs,
#     CPlugTreeVisualMip.cs and CPlugTreeLight.chunkl. A solid is a tree
#     of CPlugTree nodes, each with an optional local Location, a Visual
#     (CPlugVisualIndexedTriangles) and a Shader (usually an external
#     .Material.Gbx). -------------------------------------------------

def _solid_000(r, n):
    n["TypeAndIndex"] = r.i32()


def _solid_006(r, n):
    for _ in range(6):
        r.f32()
    for _ in range(9):
        r.f32()  # mat3


def _solid_007(r, n):
    r.bool()


def _solid_00B(r, n):
    for _ in range(6):
        r.bool()
    r.i32()


def _solid_00C(r, n):
    for _ in range(10):
        r.bool()
    r.f32()
    r.i32()
    for _ in range(4):
        r.f32()
    r.i32()
    r.i32()


def _solid_00D(r, n):
    r.bool()
    r.bool()
    n["Tree"] = _noderef(r)


def _solid_00E(r, n):
    for _ in range(4):
        r.f32()
    r.iso4()


def _solid_00F(r, n):
    r.f32()
    r.f32()


def _solid_010(r, n):
    _noderef(r)  # CSceneVehicleEnvironment


def _solid_011(r, n):
    r.bool()  # U01
    if r.bool():  # U02: has model
        r.bool()  # U03
    n["Tree"] = _noderef(r)


def _solid_012(r, n):
    r.u8()


_register(0x09005000, {
    0x09005000: (False, _solid_000),
    0x09005006: (False, _solid_006),
    0x09005007: (False, _solid_007),
    0x0900500B: (False, _solid_00B),
    0x0900500C: (False, _solid_00C),
    0x0900500D: (False, _solid_00D),
    0x0900500E: (False, _solid_00E),
    0x0900500F: (False, _solid_00F),
    0x09005010: (False, _solid_010),
    0x09005011: (False, _solid_011),
    0x09005012: (False, _solid_012),
})


def _tree_006(r, n):
    r.i32()  # "_deprec" list version
    n["Children"] = _array_noderef(r)


def _tree_00D(r, n):
    n["Name"] = r.read_id_as_string()
    r.read_id_as_string()


def _tree_011(r, n):
    n["FuncTree"] = _noderef(r)


def _tree_016(r, n):
    n["Visual"] = _noderef(r)
    n["Shader"] = _noderef(r)
    n["Surface"] = _noderef(r)
    n["Generator"] = _noderef(r)


def _tree_017(r, n):
    _noderef(r)  # CPlugVisual


def _tree_014(r, n):
    # Written by tmunlimiter_blender_plugin (plug_tree.py): Visual, (always
    # -1), Shader (external .Material.Gbx or inline CPlugMaterial), Surface,
    # Generator (always -1).
    n["Visual"] = _noderef(r)
    _noderef(r)
    n["Shader"] = _noderef(r)
    n["Surface"] = _noderef(r)
    n["Generator"] = _noderef(r)


def _tree_flags_location(r, n):
    # 0x019 (TMSX) / 0x01A (TMNESWC, TMF): flags, then Location if bit 2 (UseLocation)
    n["Flags"] = flags = r.u32()
    if flags & 4:
        n["Location"] = r.iso4()


_register(0x0904F000, {
    0x0904F006: (False, _tree_006),
    0x0904F00D: (False, _tree_00D),
    0x0904F011: (False, _tree_011),
    0x0904F014: (False, _tree_014),
    0x0904F016: (False, _tree_016),
    0x0904F017: (False, _tree_017),
    0x0904F019: (False, _tree_flags_location),
    0x0904F01A: (False, _tree_flags_location),
})


def _tree_visual_mip_002(r, n):
    count = r.i32()
    n["Levels"] = [(r.f32(), _noderef(r)) for _ in range(count)]  # (FarZ, Tree)


_register(0x09015000, {
    0x09015002: (False, _tree_visual_mip_002),
}, bases=(0x0904F000,))


def _tree_light_004(r, n):
    n["PlugLight"] = _noderef(r)


_register(0x09062000, {
    0x09062004: (False, _tree_light_004),
}, bases=(0x0904F000,))


# --- CFunc* animation nodes referenced by CPlugTree.FuncTree (0x0904F011),
#     from GBX.NET's .chunkl schemas: CFuncPlug 0x0500B000 -> CFuncTree
#     0x0501C000 -> CFuncTreeSubVisualSequence 0x05031000 (e.g. TMNF
#     StadiumWarpFlags: switches between sub-visuals), CFuncTreeRotate,
#     CFuncTreeTranslate; CFuncKeys 0x05002000 -> CFuncKeysNatural. Parsed
#     only to get past them -- the animation itself isn't imported. --------

def _func_plug_003(r, n):
    r.f32()  # Period
    r.f32()  # Phase
    r.bool()  # AutoCreateMotion


def _func_plug_004(r, n):
    _func_plug_003(r, n)
    r.bool()  # RandomizePhase


def _func_plug_005(r, n):
    _func_plug_004(r, n)
    r.read_id_as_string()  # InputValId


_register(0x0500B000, {
    0x0500B003: (False, _func_plug_003),
    0x0500B004: (False, _func_plug_004),
    0x0500B005: (False, _func_plug_005),
})
_register(0x0501C000, {}, bases=(0x0500B000,))  # CFuncTree (abstract)


def _func_keys_001(r, n):
    n["Xs"] = r.array_f32()


def _func_keys_003(r, n):
    r.read_id_as_string()


_register(0x05002000, {
    0x05002001: (False, _func_keys_001),
    0x05002003: (False, _func_keys_003),
})


def _func_keys_natural_000(r, n):
    n["Naturals"] = r.array_i32()


_register(0x05030000, {
    0x05030000: (False, _func_keys_natural_000),
}, bases=(0x05002000,))


def _func_tree_sub_visual_sequence_000(r, n):
    n["SubKeys"] = _read_node_direct(r, 0x05030000)


def _func_tree_sub_visual_sequence_001(r, n):
    r.read_id_as_string()


def _func_tree_sub_visual_sequence_002(r, n):
    n["SubKeys"] = _noderef(r)


def _func_tree_sub_visual_sequence_003(r, n):
    r.bool()  # SimpleModeIsLooping
    r.i32()  # SimpleModeStartIndex
    r.i32()  # SimpleModeEndIndex


_register(0x05031000, {
    0x05031000: (False, _func_tree_sub_visual_sequence_000),
    0x05031001: (False, _func_tree_sub_visual_sequence_001),
    0x05031002: (False, _func_tree_sub_visual_sequence_002),
    0x05031003: (False, _func_tree_sub_visual_sequence_003),
}, bases=(0x0501C000,))


def _func_tree_rotate_001(r, n):
    r.vec3()  # Axis
    r.f32()  # AngleMin
    r.f32()  # AngleMax


_register(0x0501E000, {
    0x0501E001: (False, _func_tree_rotate_001),
}, bases=(0x0501C000,))


def _func_tree_translate_000(r, n):
    r.vec3()  # StartPoint
    r.vec3()  # EndPoint


def _func_tree_translate_001(r, n):
    r.i32()  # Flags


_register(0x0500D000, {
    0x0500D000: (False, _func_tree_translate_000),
    0x0500D001: (False, _func_tree_translate_001),
}, bases=(0x0501C000,))


# --- TMUnlimiter custom block 0x3F002000 (.Block.Gbx written by
#     tmunlimiter_blender_plugin, github.com/tomek0055/tmunlimiter_blender_plugin).
#     Not a Nadeo class: hand-ported from that exporter's own writer
#     (block_definition.py, plug_tree.py, texture_custom.py,
#     prop_light_settings.py). The models inside are regular CPlugTree /
#     CPlugVisualIndexedTriangles / CPlugSurface nodes. -------------------

def _material_custom_006(r, n):
    count = r.i32()
    # (texture slot name, 0, instance index into the block's texture list)
    n["Textures"] = [(r.read_id_as_string(), r.i32(), r.i32()) for _ in range(count)]


def _material_custom_00C(r, n):
    count = r.i32()
    for _ in range(count):
        r.read_id_as_string()
        r.i32()


def _material_custom_00D(r, n):
    n["Flags"] = struct.unpack_from("<Q", r.bytes(8))[0]  # 4 = double sided
    r.bytes(8)  # shader requirements


_register(0x0903A000, {
    0x0903A006: (False, _material_custom_006),
    0x0903A00C: (False, _material_custom_00C),
    0x0903A00D: (False, _material_custom_00D),
})


def _plug_light_002(r, n):
    n["Light"] = _noderef(r)  # CGxLightPoint / CGxLightSpot
    _noderef(r)
    _noderef(r)
    _noderef(r)
    r.i32()


_register(0x0901D000, {
    0x0901D002: (False, _plug_light_002),
})


def _gx_light_009(r, n):
    n["Color"] = r.vec3()
    r.u32()  # flags
    n["Intensity"] = r.f32()
    for _ in range(8):
        r.f32()


def _gx_light_ball_004(r, n):
    r.f32()
    r.f32()


def _gx_light_point_006(r, n):
    r.u32()
    n["Radius"] = r.f32()
    for _ in range(9):
        r.f32()


def _gx_light_spot_002(r, n):
    r.u32()
    for _ in range(6):
        r.f32()


_register(0x04002000, {  # CGxLightPoint
    0x04001009: (False, _gx_light_009),
    0x04003004: (False, _gx_light_ball_004),
    0x04002006: (False, _gx_light_point_006),
})
_register(0x0400B000, {  # CGxLightSpot
    0x0400B002: (False, _gx_light_spot_002),
}, bases=(0x04002000,))


def _read_block_variations(r, n, trigger_allowed, with_pre_light_gen):
    count = r.u8()
    variations = []
    for _ in range(count):
        model = _noderef(r)
        trigger = _noderef(r) if trigger_allowed else None
        if with_pre_light_gen:
            r.u8()  # pre_light_gen_tile_count (newer exporter versions only)
        variations.append({"Model": model, "Trigger": trigger})
    return variations


def _read_block_body(r, n, with_pre_light_gen, with_texture_options=True):
    flags = n["Flags"]
    is_road = ((flags >> 1) & 3) == 3
    trigger_allowed = ((flags >> 4) & 7) in (1, 2, 4)  # finish, checkpoint, multilap

    replacement_flags = r.u8()
    for _ in range(bin(replacement_flags & 0x0F).count("1")):
        r.u32()  # replacement texture instance index

    textures = {}
    for _ in range(r.i32()):
        instance_index = r.i32()
        textures[instance_index] = r.string()  # file path
        if with_texture_options:
            r.u8()  # filtering
            r.u8()  # addressing
    n["CustomTextures"] = textures

    n["Variants"] = []
    for _ in range(6 if is_road else 1):
        ground = _read_block_variations(r, n, trigger_allowed, with_pre_light_gen)
        air = _read_block_variations(r, n, trigger_allowed, with_pre_light_gen)
        n["Variants"].append({"Ground": ground, "Air": air})

    def spawn():
        # (location.y, location.z, location.x, rotation.y, rotation.z, rotation.x) of the Blender empty
        return [r.f32() for _ in range(6)]

    n["GroundSpawn"] = spawn()
    n["AirSpawn"] = spawn()

    ground_units = r.i32()
    air_units = r.i32()
    n["GroundBlockUnits"] = [(r.i32(), r.i32(), r.i32()) for _ in range(ground_units)]
    n["AirBlockUnits"] = [(r.i32(), r.i32(), r.i32()) for _ in range(air_units)]

    if flags & 1:  # backward compatibility model
        n["BackwardCompatibilityModel"] = _noderef(r)

    # Newer TMUnlimiter versions: optional block script (AngelScript source,
    # e.g. "bool onVehicleCollision(TrackManiaRace@ race, ...)")
    if r.pos < getattr(r, "chunk_end", len(r.data)) and r.u8():
        n["Script"] = r.string()


def _block_002(r, n):
    header = _GbxReader(n.get("_header_chunks", {}).get(0x3F002002, b""))
    n["Identifier"] = header.read_id_as_string() if header.data else ""
    n["Author"] = header.read_id_as_string() if header.data else ""
    n["Flags"] = header.u8() if header.data else 0

    # Exporter versions differ slightly (newer ones write one extra byte per
    # variation, pre_light_gen_tile_count; older ones may not write the
    # custom texture options): try each layout, keep the one that ends
    # exactly at the end of this chunk.
    end = r.chunk_end
    start, node_dict, id_dict, id_version = r.pos, dict(r.node_dict), dict(r.id_dict), r.id_version
    for with_pre_light_gen in (True, False):
        for with_texture_options in (True, False):
            r.pos, r.node_dict, r.id_dict, r.id_version = start, dict(node_dict), dict(id_dict), id_version
            try:
                _read_block_body(r, n, with_pre_light_gen, with_texture_options)
                if r.pos == end:
                    return
            except Exception:
                pass
    raise ValueError("could not read this TMUnlimiter block's body (unknown exporter version)")


_register(0x3F002000, {
    0x3F002001: (True, _block_002),  # older exporter versions
    0x3F002002: (True, _block_002),
})


# =======================================================================
# Top-level .Gbx file parsing (header + LZO body decompression + root
# node) and item-mesh extraction.
# =======================================================================

def _parse_header_user_data(r, user_data_len, class_id, raw_chunks=None):
    """Header user data is a table-of-contents (chunk id + size pairs)
    followed by each chunk's raw data in the same order. We only care
    about one value from it: CGameItemModel's own header chunk (id ==
    the class id itself, suffix 0x000) holds ItemType as its first int,
    needed to correctly parse body chunk 0x2E002019's legacy fields."""
    end = r.pos + user_data_len
    item_type = None

    num_chunks = r.i32()
    if num_chunks > 0:
        descriptors = [(r.u32(), r.u32() & 0x7FFFFFFF) for _ in range(num_chunks)]
        for chunk_id, size in descriptors:
            chunk_start = r.pos
            if raw_chunks is not None:
                raw_chunks[chunk_id] = r.data[chunk_start:chunk_start + size]
            if chunk_id == class_id and size >= 4:
                item_type = r.i32()
            r.pos = chunk_start + size

    if r.pos < end:
        r.bytes(end - r.pos)
    elif r.pos > end:
        raise ValueError("header user data overrun")

    return item_type


def _read_ref_table(r, version):
    """Ref table (external nodes), hand-ported from GBX.NET's
    GbxRefTableReader.cs. Returns {node index: relative file path}, e.g.
    {6: "Material/StadiumRoad.Material.Gbx"} for a TMNF .Solid.Gbx."""
    num_external_nodes = r.i32()
    if num_external_nodes <= 0:
        return {}

    r.i32()  # ancestor level

    directories = []

    def read_children(parent):
        for _ in range(r.i32()):
            name = r.string()
            path = f"{parent}/{name}" if parent else name
            directories.append(path)
            read_children(path)

    read_children("")

    external = {}
    for _ in range(num_external_nodes):
        flags = r.i32()
        if flags & 4:  # resource
            name = f"<resource {r.i32()}>"
            node_index = r.i32()
            if version >= 5:
                r.bool()  # use file
        else:
            name = r.string()
            node_index = r.i32()
            if version >= 5:
                r.bool()  # use file
            dir_index = r.i32() - 1
            if dir_index >= 0:
                name = f"{directories[dir_index]}/{name}"
        external[node_index] = name
    return external


def _parse_gbx_root_node(filepath):
    data = Path(filepath).read_bytes()
    r = _GbxReader(data)

    magic = r.bytes(3)
    if magic != b"GBX":
        raise ValueError(f"'{filepath}' is not a GBX file (bad magic)")

    version = r.u16()
    r.u8()  # format ('B'inary or 'T'ext -- always Binary in practice)
    r.u8()  # ref-table compression
    comp_body = chr(r.u8())
    if version >= 4:
        r.u8()  # unknown byte
    class_id = r.u32()

    item_type = None
    header_chunks = {}
    if version >= 6:
        user_data_len = r.i32()
        if user_data_len > 0:
            item_type = _parse_header_user_data(r, user_data_len, class_id, header_chunks)

    r.i32()  # num nodes
    external = _read_ref_table(r, version)

    if comp_body == "C":
        uncompressed_size = r.u32()
        compressed_size = r.u32()
        compressed = r.bytes(compressed_size)
        body = _lzo1x_decompress(compressed, uncompressed_size)
    else:
        body = r.bytes(len(data) - r.pos)

    body_reader = _GbxReader(body)
    body_reader.external = external
    node = {"_class": class_id, "_class_hex": f"0x{class_id:08X}", "_item_type": item_type,
            "_header_chunks": header_chunks}
    parser = _NODE_PARSERS.get(class_id)
    if parser is None:
        raise ValueError(f"unsupported root class 0x{class_id:08X}")
    _read_node_body(body_reader, node, _NODE_PARSERS, parser)
    return node


def _resolve_vis_model_mesh(vis_model, source_dir):
    """Resolve a CGameObjectVisModel (0x2E007000) node down to a mesh,
    returned as (kind, node), or raise a clear error. Handles all three
    of its possible mesh representations: an inline CPlugSolid2Model, a
    filename referencing a sibling .Mesh.Gbx file, or the legacy
    CPlugSolid/CPlugTree format (unsupported)."""
    if vis_model.get("MeshShaded"):
        return ("solid2", vis_model["MeshShaded"])

    mesh_filename = vis_model.get("Mesh")
    if mesh_filename:
        mesh_path = _find_file_ignore_case(source_dir, mesh_filename)
        if not mesh_path.is_file():
            raise RuntimeError(
                f"This item references a sibling mesh file "
                f"'{mesh_filename}' that doesn't exist next to it."
            )
        mesh_node = _parse_gbx_root_node(str(mesh_path))
        if mesh_node.get("_class") == 0x090BB000:
            return ("solid2", mesh_node)
        raise RuntimeError(
            f"This item's sibling mesh file uses class "
            f"0x{mesh_node.get('_class', 0):08X}, which this "
            f"pure-Python importer doesn't support yet."
        )

    if vis_model.get("Solid"):
        raise RuntimeError(
            "This item's mesh uses the legacy CPlugSolid/CPlugTree "
            "format, which this pure-Python importer doesn't "
            "support yet."
        )

    raise RuntimeError(
        "This item has no mesh that could be imported "
        "(it may be a materials-only/utility item)."
    )


def _extract_mesh(item_node, source_dir):
    """Find this item's mesh (Crystal or Solid2), returned as
    (kind, node), or raise a clear error describing why it can't be
    imported yet. `source_dir` is the .Item.Gbx's own directory, needed
    to resolve items whose mesh is just a filename referencing a sibling
    .Mesh.Gbx file."""
    edition = item_node.get("EntityModelEdition")
    if edition is not None and edition.get("_class") == 0x2E026000 and edition.get("MeshCrystal"):
        return ("crystal", edition["MeshCrystal"])

    entity_model = item_node.get("EntityModel")
    if entity_model is not None and entity_model.get("_class") == 0x2E027000:
        static_object = entity_model.get("StaticObject")
        mesh = static_object.get("Mesh") if static_object else None
        if mesh:
            return ("solid2", mesh)

        vis_model = entity_model.get("VisModel")
        if vis_model is not None:
            return _resolve_vis_model_mesh(vis_model, source_dir)

        raise RuntimeError(
            "This item has no mesh that could be imported "
            "(it may be a materials-only/utility item)."
        )

    if entity_model is not None or (edition is not None and edition.get("MeshCrystal") is None):
        raise RuntimeError(
            "This item's mesh uses a format (Prefab / legacy CPlugSolid) "
            "that this pure-Python importer doesn't support yet."
        )

    # Oldest format: CGameItemModel stores the mesh directly under its
    # own VisModelCustom field (no EntityModel/EntityModelEdition at all).
    vis_model_custom = item_node.get("VisModelCustom")
    if vis_model_custom is not None and vis_model_custom.get("_class") == 0x2E007000:
        return _resolve_vis_model_mesh(vis_model_custom, source_dir)

    raise RuntimeError(
        "This item has no mesh that could be imported "
        "(it may be a materials-only/utility item)."
    )


# =======================================================================
# Blender mesh building.
# =======================================================================

def _get_material(name):
    """Get or create a simple placeholder material for `name` (Nadeo
    material path, e.g. "Stadium\\Media\\Material\\StadiumRoad")."""
    if not name:
        name = "Default"
    short_name = name.rsplit("\\", 1)[-1][:63]
    mat = bpy.data.materials.get(short_name)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(short_name)
    mat.use_nodes = True
    # Deterministic-but-distinct color per material name, just so different
    # materials are visually distinguishable without needing real textures.
    h = abs(hash(name))
    color = ((h & 0xFF) / 255, ((h >> 8) & 0xFF) / 255, ((h >> 16) & 0xFF) / 255, 1.0)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = color
    return mat


class _MeshBuilder:
    """Accumulates faces (with per-face UVs and a material name), then
    builds one combined Blender mesh object at the end."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.uv_layer = self.bm.loops.layers.uv.new("UVMap")
        self.material_names = []
        self._material_index = {}

    def _mat_index(self, name):
        idx = self._material_index.get(name)
        if idx is None:
            idx = len(self.material_names)
            self._material_index[name] = idx
            self.material_names.append(name or "Default")
        return idx

    def _extra_uv_layer(self, index):
        """UV layer #index (1, 2...) beyond the first, created on demand."""
        layers = self.bm.loops.layers.uv
        while len(layers) <= index:
            layers.new(f"UVMap.{len(layers):03d}")
        return layers[index]

    def add_triangle(self, positions, uvs, material_name, transform, extra_uvs=()):
        """positions/uvs: 3 x (x,y,z) / (u,v) tuples, already in Nadeo's
        own Y-up coordinate space; `transform` maps local -> parent space.
        extra_uvs: one 3 x (u,v) tuple per additional UV layer."""
        try:
            verts = [self.bm.verts.new(transform @ Vector(p)) for p in positions]
            face = self.bm.faces.new(verts)
        except ValueError:
            return  # degenerate/duplicate face, skip
        face.material_index = self._mat_index(material_name)
        for loop, uv in zip(face.loops, uvs):
            loop[self.uv_layer].uv = uv
        for layer_index, layer_uvs in enumerate(extra_uvs, start=1):
            layer = self._extra_uv_layer(layer_index)
            for loop, uv in zip(face.loops, layer_uvs):
                loop[layer].uv = uv

    def add_ngon(self, positions, uvs, material_name, transform):
        """Fan-triangulate an n-gon (Crystal faces aren't always triangles)."""
        for i in range(1, len(positions) - 1):
            self.add_triangle(
                (positions[0], positions[i], positions[i + 1]),
                (uvs[0], uvs[i], uvs[i + 1]),
                material_name, transform,
            )

    def finish(self, collection):
        mesh = bpy.data.meshes.new(self.name)
        self.bm.normal_update()
        self.bm.to_mesh(mesh)
        self.bm.free()

        for mat_name in self.material_names:
            mesh.materials.append(_get_material(mat_name))

        obj = bpy.data.objects.new(self.name, mesh)
        collection.objects.link(obj)
        return obj


def _add_crystal(builder, crystal_node, transform):
    if not crystal_node:
        return

    for layer in crystal_node.get("Layers", []):
        if layer.get("_type") != "Geometry":
            continue
        if not layer.get("IsEnabled", True) or not layer.get("IsVisible", True):
            continue

        geo = layer["Crystal"]
        positions = geo["Positions"]

        for face in geo["Faces"]:
            verts = face["Vertices"]
            if len(verts) < 3:
                continue
            pos_list = [positions[v["Index"]] for v in verts]
            uv_list = [(v["TexCoord"][0], 1 - v["TexCoord"][1]) for v in verts]
            material_name = _material_display_name(face.get("Material")) or "Default"
            builder.add_ngon(pos_list, uv_list, material_name, transform)


def _add_solid2(builder, solid2_node, transform):
    if not solid2_node:
        return

    visuals = solid2_node.get("Visuals") or []

    for geom in solid2_node.get("ShadedGeoms") or []:
        visual_index = geom.get("VisualIndex", -1)
        if visual_index < 0 or visual_index >= len(visuals):
            continue
        visual = visuals[visual_index]
        if not visual:
            continue

        index_buffer = visual.get("IndexBuffer")
        if not index_buffer:
            continue

        vertex_streams = visual.get("VertexStreams") or []
        if vertex_streams:
            vertex_stream = vertex_streams[0]
            positions = vertex_stream.get("Positions") if vertex_stream else None
            uv0 = (vertex_stream.get("UVs") or {}).get(0)
        else:
            # Older visuals embed vertex data directly in the visual
            # itself (no CPlugVertexStream indirection).
            positions = visual.get("Vertices")
            tex_coord_sets = visual.get("TexCoords") or []
            uv0 = tex_coord_sets[0] if tex_coord_sets else None
        if not positions:
            continue
        indices = index_buffer.get("Indices") or []

        material_name = _solid2_material_name(solid2_node, geom.get("MaterialIndex", -1)) or "Default"

        for i in range(0, len(indices) - 2, 3):
            i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]
            if i0 >= len(positions) or i1 >= len(positions) or i2 >= len(positions):
                continue
            tri_pos = (positions[i0], positions[i1], positions[i2])
            if uv0 and i0 < len(uv0) and i1 < len(uv0) and i2 < len(uv0):
                tri_uv = (
                    (uv0[i0][0], 1 - uv0[i0][1]),
                    (uv0[i1][0], 1 - uv0[i1][1]),
                    (uv0[i2][0], 1 - uv0[i2][1]),
                )
            else:
                tri_uv = ((0, 0), (0, 0), (0, 0))
            builder.add_triangle(tri_pos, tri_uv, material_name, transform)


def import_item_gbx(filepath):
    """Parse a ManiaPlanet .Item.Gbx file (pure Python, no external tool)
    and build a Blender mesh object from its geometry (CPlugCrystal for
    'customizable' items, CPlugSolid2Model for plain static items)."""
    item_node = _parse_gbx_root_node(filepath)

    if item_node.get("_class") != 0x2E002000:
        raise RuntimeError(f"'{filepath}' is not a .Item.Gbx (CGameItemModel) file")

    kind, mesh_node = _extract_mesh(item_node, Path(filepath).resolve().parent)

    name = _strip_gbx_suffixes(Path(filepath).name)
    builder = _MeshBuilder(name)

    if kind == "crystal":
        _add_crystal(builder, mesh_node, _COORD_CONVERT)
    else:
        _add_solid2(builder, mesh_node, _COORD_CONVERT)

    if not builder.bm.faces:
        builder.bm.free()
        raise RuntimeError("This item has no mesh that could be imported "
                            "(it may be a materials-only/utility item).")

    return builder.finish(bpy.context.collection)


def _iso4_to_matrix(iso4):
    if not iso4:
        return Matrix.Identity(4)
    return Matrix((
        (iso4["XX"], iso4["XY"], iso4["XZ"], iso4["TX"]),
        (iso4["YX"], iso4["YY"], iso4["YZ"], iso4["TY"]),
        (iso4["ZX"], iso4["ZY"], iso4["ZZ"], iso4["TZ"]),
        (0, 0, 0, 1),
    ))


def _external_material_name(shader):
    """"Material/StadiumRoad.Material.Gbx" -> "StadiumRoad" (TMNF material name)."""
    path = (shader or {}).get("_external")
    if not path:
        return None
    file_name = path.replace("\\", "/").rsplit("/", 1)[-1]
    if file_name.lower().endswith(".material.gbx"):
        return file_name[:-len(".material.gbx")]
    return _strip_gbx_suffixes(file_name)


_BOX_CORNERS = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
_BOX_TRIANGLES = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
                  (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]


def _add_surf(builder, surf, material_name, transform):
    """Collision shape (CPlugSurface surf) -> triangles. Mesh, Box and
    Compound only; spheres/ellipsoids etc. are skipped."""
    if not surf:
        return
    no_uv = ((0, 0), (0, 0), (0, 0))
    if surf.get("Vertices") is not None:
        vertices = surf["Vertices"]
        for i0, i1, i2 in surf.get("Triangles") or []:
            if max(i0, i1, i2) < len(vertices):
                builder.add_triangle((vertices[i0], vertices[i1], vertices[i2]), no_uv, material_name, transform)
    elif surf.get("Box"):
        cx, cy, cz, hx, hy, hz = surf["Box"]
        corners = [(cx + sx * hx, cy + sy * hy, cz + sz * hz) for sx, sy, sz in _BOX_CORNERS]
        for i0, i1, i2 in _BOX_TRIANGLES:
            builder.add_triangle((corners[i0], corners[i1], corners[i2]), no_uv, material_name, transform)
    for sub_surf, location in zip(surf.get("Surfs") or [], surf.get("SurfLocs") or []):
        _add_surf(builder, sub_surf, material_name, transform @ _iso4_to_matrix(location))


# Collision-only solids are checkpoint/finish triggers: their surface
# material (e.g. StadiumRoadBorder) is only the physics surface type, not a
# visible material, so they get one plain yellow "Trigger" material instead.
_TRIGGER_MATERIAL = "Trigger"
_TRIGGER_COLOR = (1.0, 0.8, 0.0, 1.0)


def _get_trigger_material():
    mat = bpy.data.materials.get(_TRIGGER_MATERIAL) or bpy.data.materials.new(_TRIGGER_MATERIAL)
    mat.use_nodes = True
    mat.diffuse_color = _TRIGGER_COLOR  # viewport (Solid mode)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = _TRIGGER_COLOR
    return mat


def _add_solid_tree(builder, tree, transform, collision_builder=None):
    """Walk a CPlugTree (same traversal as GBX.NET's
    CPlugTree.GetAllChildrenWithLocation, LOD 0 only). Trees with a
    collision surface but no visual (triggers, invisible walls) go to
    `collision_builder`."""
    if not tree or "_external" in tree:
        return

    transform = transform @ _iso4_to_matrix(tree.get("Location"))

    visual = tree.get("Visual")
    surface = tree.get("Surface")
    if collision_builder is not None and not visual and surface and "_external" not in surface:
        geom = surface.get("Geom") or {}
        _add_surf(collision_builder, geom.get("Surf"), _TRIGGER_MATERIAL, transform)

    if visual and "_external" not in visual:
        positions = visual.get("Vertices")
        indices = (visual.get("IndexBuffer") or {}).get("Indices") or []
        tex_coord_sets = [uv_set for uv_set in (visual.get("TexCoords") or []) if len(uv_set) == len(positions or ())]
        material_name = _external_material_name(tree.get("Shader")) or "Default"

        if positions:
            for i in range(0, len(indices) - 2, 3):
                i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]
                if i0 >= len(positions) or i1 >= len(positions) or i2 >= len(positions):
                    continue
                tri_pos = (positions[i0], positions[i1], positions[i2])
                # UVs as-is, no V flip: exact inverse of tmunlimiter's exporter
                # (it writes Blender UVs unchanged into this same 0x0900600E
                # format), all sets in order (base, then lightmap/occlusion).
                tri_uvs = [(uv_set[i0], uv_set[i1], uv_set[i2]) for uv_set in tex_coord_sets]
                if not tri_uvs:
                    tri_uvs = [((0, 0), (0, 0), (0, 0))]
                builder.add_triangle(tri_pos, tri_uvs[0], material_name, transform, extra_uvs=tri_uvs[1:])

    # CPlugTreeVisualMip: only the most detailed level (smallest FarZ)
    levels = tree.get("Levels")
    if levels:
        _add_solid_tree(builder, min(levels, key=lambda level: level[0])[1], transform, collision_builder)

    for child in tree.get("Children") or []:
        _add_solid_tree(builder, child, transform, collision_builder)


def import_solid_gbx(filepath):
    """Parse a TMNF/TMUF .Solid.Gbx file (CPlugSolid -> CPlugTree hierarchy)
    and build a Blender mesh object from its visuals, one material slot per
    TMNF material (named like the game material, e.g. "StadiumRoad"). A
    solid with no visual at all (e.g. a checkpoint Trigger.Solid.Gbx) is
    imported from its collision-only parts instead. Returns the list of
    created objects."""
    solid_node = _parse_gbx_root_node(filepath)

    if solid_node.get("_class") != 0x09005000:
        raise RuntimeError(f"'{filepath}' is not a .Solid.Gbx (CPlugSolid) file")

    name = _strip_gbx_suffixes(Path(filepath).name)
    builder = _MeshBuilder(name)
    collision_builder = _MeshBuilder(f"{name}_Collision")
    _add_solid_tree(builder, solid_node.get("Tree"), _TMUNLIMITER_CONVERT, collision_builder)

    # Regular blocks: visual only (their collision-only parts would just
    # clutter the import). Collision only when there's nothing else.
    chosen = builder if builder.bm.faces else collision_builder
    for mesh_builder in (builder, collision_builder):
        if mesh_builder is not chosen:
            mesh_builder.bm.free()

    if not chosen.bm.faces:
        chosen.bm.free()
        raise RuntimeError("This solid has no mesh that could be imported.")

    if chosen is collision_builder:
        # Material created before finish() so it isn't given a random color
        _get_trigger_material()
    return [chosen.finish(bpy.context.collection)]


# =======================================================================
# TMUnlimiter .Block.Gbx -> Blender objects. One object per CPlugTree, same
# parent/child hierarchy, transforms, names, UVs and normals as written by
# tmunlimiter_blender_plugin's exporter, plus its object/material settings
# (when that addon is enabled) so the block can be re-exported as is.
# =======================================================================

def _tmunlimiter_object_settings(obj):
    return getattr(obj, "unlimiter_object_settings", None)


def _collision_material_name(surface_id):
    """tmunlimiter collision material id (e.g. 16) -> "Collision_Asphalt"."""
    import sys
    module = sys.modules.get("tmunlimiter_blender_plugin.material_collision.default_collision_materials")
    for identifier, name, _description in getattr(module, "DEFAULT_COLLISION_MATERIALS", ()):
        if identifier == str(surface_id):
            return "Collision_" + name.split(": ", 1)[-1]
    return f"Collision_{surface_id}"


def _set_material_collision(mat, surface_id):
    collision = getattr(mat, "unlimiter_material_collision", None)
    if collision is not None and surface_id is not None:
        collision.is_collidable = True
        try:
            collision.collision_material = str(surface_id)
        except TypeError:
            pass


def _surface_ids(surface):
    return [(m or {}).get("SurfaceId") for m in (surface or {}).get("Materials") or []]


def _block_visual_mesh(name, visual):
    """CPlugVisualIndexedTriangles -> Blender mesh, vertices shared exactly
    like tmunlimiter wrote them (game Y-up -> Blender with _TMUNLIMITER_CONVERT)."""
    positions = [tuple(_TMUNLIMITER_CONVERT @ Vector(p)) for p in visual.get("Vertices") or []]
    indices = (visual.get("IndexBuffer") or {}).get("Indices") or []
    faces = [tuple(indices[i:i + 3]) for i in range(0, len(indices) - 2, 3)
             if max(indices[i:i + 3]) < len(positions)]
    if not positions or not faces:
        return None

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(positions, [], faces)

    for layer_index, uv_set in enumerate(visual.get("TexCoords") or []):
        if len(uv_set) != len(positions):
            continue
        layer = mesh.uv_layers.new(name="BaseMaterial" if layer_index == 0 else f"UVMap.{layer_index:03d}")
        for loop in mesh.loops:
            layer.data[loop.index].uv = uv_set[loop.vertex_index]  # as-is, like tmunlimiter writes them

    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    normals = visual.get("Normals") or []
    if len(normals) == len(positions):
        try:
            mesh.normals_split_custom_set_from_vertices(
                [tuple((_TMUNLIMITER_CONVERT.to_3x3() @ Vector(nrm)).normalized()) for nrm in normals])
        except Exception:
            pass
    mesh.update()
    return mesh


def _block_surface_mesh(name, surf):
    """Collision-only CPlugSurface mesh -> Blender mesh, one material slot
    per collision material index."""
    vertices = [tuple(_TMUNLIMITER_CONVERT @ Vector(p)) for p in (surf or {}).get("Vertices") or []]
    triangles = [t for t in (surf or {}).get("Triangles") or [] if max(t) < len(vertices)]
    if not vertices or not triangles:
        return None, []
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], triangles)
    material_indices = list((surf.get("TriangleMaterials") or [0] * len(triangles))[:len(triangles)])
    mesh.polygons.foreach_set("material_index", material_indices)
    mesh.update()
    return mesh, sorted(set(material_indices))


def _block_material(shader, custom_textures):
    """Material for a tree's Shader: external game material
    ("Stadium/Media/Material/StadiumRoad.Material.Gbx" -> "StadiumRoad"), or
    tmunlimiter custom material (named after its diffuse texture).
    Returns (material, ("Game", environment, file) | ("Custom", {slot: path}) | None)."""
    if not shader:
        return None, None
    if "_external" in shader:
        path = shader["_external"].replace("\\", "/")
        name = _external_material_name(shader)
        return _get_material(name), ("Game", path.split("/", 1)[0], path.rsplit("/", 1)[-1])
    textures = {}
    for slot, _zero, instance_index in (shader.get("Custom") or {}).get("Textures") or []:
        if instance_index in custom_textures:
            textures[slot] = custom_textures[instance_index]
    diffuse = textures.get("Diffuse")
    name = Path(diffuse.replace("\\", "/")).stem if diffuse else "CustomMaterial"
    return _get_material(name), ("Custom", textures)


def _apply_texture_settings(obj, texture_info):
    settings = _tmunlimiter_object_settings(obj)
    if settings is None or not texture_info:
        return
    texture_props = settings.texture_props
    try:
        if texture_info[0] == "Game":
            _kind, environment, file_name = texture_info
            texture_props.texture_type = "Game"
            texture_game = texture_props.texture_game
            texture_game.environment = {"Desert": "Speed", "Snow": "Alpine"}.get(environment, environment)
            texture_game.game_material = file_name
        else:
            texture_props.texture_type = "Custom"
            custom = texture_props.texture_custom
            for slot, attr in (("Diffuse", "diffuse"), ("Specular", "specular"), ("Normal", "normal"),
                               ("Lighting", "lighting"), ("Occlusion", "occlusion")):
                use = slot in texture_info[1]
                setattr(custom, f"use_{attr}", use)
                if use:
                    getattr(custom, attr).filepath = texture_info[1][slot]
    except (TypeError, AttributeError):
        pass  # unknown environment/material for this tmunlimiter version


def _block_tree_object(tree, name, collection, parent, context, is_trigger):
    """Create the Blender object for one CPlugTree (+ its children)."""
    if tree is None or "_external" in tree:
        return None
    built = context["built"]
    if id(tree) in built:
        return built[id(tree)]

    visual = tree.get("Visual") if tree.get("Visual") and "_external" not in tree.get("Visual") else None
    surface = tree.get("Surface") if tree.get("Surface") and "_external" not in tree.get("Surface") else None
    # Unnamed collision-only object: "<block>_Col" (same convention as the user's own blocks)
    obj_name = tree.get("Name") or (f"{name}_Col" if surface is not None and visual is None and not is_trigger else name)
    data = None
    texture_info = None
    collision_only = False

    if tree.get("_class") == 0x09062000:  # CPlugTreeLight
        light_node = ((tree.get("PlugLight") or {}).get("Light")) or {}
        light = bpy.data.lights.new(obj_name, "SPOT" if light_node.get("_class") == 0x0400B000 else "POINT")
        if light_node.get("Color"):
            light.color = light_node["Color"]
        data = light
    elif visual is not None:
        data = _block_visual_mesh(obj_name, visual)
        if data is not None:
            mat, texture_info = _block_material(tree.get("Shader"), context["custom_textures"])
            if mat is not None:
                data.materials.append(mat)
                ids = _surface_ids(surface)
                if ids:
                    _set_material_collision(mat, ids[0])
    elif surface is not None:
        data, material_indices = _block_surface_mesh(obj_name, (surface.get("Geom") or {}).get("Surf"))
        if data is not None:
            collision_only = True
            ids = _surface_ids(surface)
            for material_index in range(max(material_indices) + 1 if material_indices else 0):
                if is_trigger:
                    mat = _get_trigger_material()
                else:
                    surface_id = ids[material_index] if material_index < len(ids) else None
                    mat = _get_material(_collision_material_name(surface_id))
                    _set_material_collision(mat, surface_id)
                data.materials.append(mat)

    obj = bpy.data.objects.new(obj_name, data)
    collection.objects.link(obj)
    built[id(tree)] = obj
    if parent is not None:
        obj.parent = parent
    obj.matrix_basis = _TMUNLIMITER_CONVERT @ _iso4_to_matrix(tree.get("Location")) @ _TMUNLIMITER_CONVERT.inverted()

    colors = (visual or {}).get("Colors") or []
    if colors:
        obj.color = colors[0]

    settings = _tmunlimiter_object_settings(obj)
    if settings is not None:
        settings.can_export_object_name = bool(tree.get("Name"))
        if obj.type == "MESH":
            settings.can_export_geometry = not collision_only
            settings.can_export_collision = surface is not None
        if tree.get("_class") == 0x09015000:
            settings.is_visual_mip = True
    _apply_texture_settings(obj, texture_info)

    for child in tree.get("Children") or []:
        _block_tree_object(child, name, collection, obj, context, is_trigger)
    for far_z, level in tree.get("Levels") or []:  # CPlugTreeVisualMip LODs
        level_obj = _block_tree_object(level, name, collection, obj, context, is_trigger)
        level_settings = _tmunlimiter_object_settings(level_obj) if level_obj else None
        if level_settings is not None:
            level_settings.visual_mip_distance = far_z
    return obj


# Road block variants, in tmunlimiter's archive order (block_definition.get_available_variants)
_ROAD_VARIANT_NAMES = ("Piece", "Deadend", "Turn", "Straight", "TJunction", "CrossJunction")


def import_block_gbx(filepath, parent_collection=None):
    """Parse a TMUnlimiter custom block (.Block.Gbx, class 0x3F002000) and
    rebuild it: every variation's model and trigger as an object hierarchy,
    the spawn locations as empties and the block units on the grid of the
    environment chosen in Detection Units. Returns the block's collection."""
    block = _parse_gbx_root_node(filepath)
    if block.get("_class") != 0x3F002000:
        raise RuntimeError(f"'{filepath}' is not a TMUnlimiter .Block.Gbx file")
    if "Variants" not in block:
        raise RuntimeError("This block has no content that could be imported.")

    name = block.get("Identifier") or _strip_gbx_suffixes(Path(filepath).name)
    parent_collection = parent_collection or bpy.context.collection
    collection = bpy.data.collections.new(name)
    parent_collection.children.link(collection)

    # Object names say which variation they belong to, e.g. "RoadGridBoosterR_Ground" /
    # "RoadGridBoosterR_Air" (+ the variant for road blocks: "..._Straight_Ground").
    variants = block["Variants"]
    has_both_kinds = any(v["Ground"] for v in variants) and any(v["Air"] for v in variants)
    variant_names = _ROAD_VARIANT_NAMES if len(variants) > 1 else ("",)

    context = {"built": {}, "custom_textures": block.get("CustomTextures") or {}}
    for variant_name, variant in zip(variant_names, variants):
        for kind in ("Ground", "Air"):
            for index, variation in enumerate(variant[kind]):
                base = name
                if variant_name:
                    base += f"_{variant_name}"
                if has_both_kinds:
                    base += f"_{kind}"
                if len(variant[kind]) > 1:
                    base += f"_{index + 1}"
                _block_tree_object(variation["Model"], base, collection, None, context, False)
                _block_tree_object(variation["Trigger"], f"{base}_Trigger", collection, None, context, True)
    _block_tree_object(block.get("BackwardCompatibilityModel"), name, collection, None, context, False)

    # Spawns: (location.y, location.z, location.x, rotation.y, rotation.z, rotation.x)
    for spawn_name, spawn in (("Spawn_Ground", block.get("GroundSpawn")), ("Spawn_Air", block.get("AirSpawn"))):
        if spawn and any(abs(v) > 0.0 for v in spawn):
            empty = bpy.data.objects.new(spawn_name, None)
            empty.empty_display_type = "ARROWS"
            empty.empty_display_size = 2.0
            empty.location = (spawn[2], spawn[0], spawn[1])
            empty.rotation_euler = (spawn[5], spawn[3], spawn[4])
            collection.objects.link(empty)

    # Block script (newer TMUnlimiter versions): kept as a Blender text, linked to the collection
    if block.get("Script"):
        text = bpy.data.texts.new(f"{name}.as")
        text.write(block["Script"])
        collection["tmu_block_script"] = text.name

    _create_block_units(block)
    return collection


def _create_block_units(block):
    """Block units (offsets (y, z, x) in blocks) -> empties on the Detection
    Units grid, reusing the ones already there."""
    offsets = set(block.get("GroundBlockUnits") or []) | set(block.get("AirBlockUnits") or [])
    if not offsets:
        return
    from .Detection import grid_settings, create_or_get_collection, add_empty_cube
    environment = getattr(bpy.context.scene, "block_units_environment", "STADIUM")
    _start, scale, _sx, _sy, _sz = grid_settings(environment)
    size = (2 * scale[0], 2 * scale[1], 2 * scale[2])
    existing = {tuple(round(v, 3) for v in obj.location): obj for obj in bpy.context.scene.objects
                if obj.type == "EMPTY" and obj.empty_display_type == "CUBE"}
    units_collection = None
    for row, layer, col in sorted(offsets):
        location = (scale[0] + col * size[0], scale[1] + row * size[1], scale[2] + layer * size[2])
        if tuple(round(v, 3) for v in location) in existing:
            continue
        if units_collection is None:
            units_collection = create_or_get_collection("BlockUnits", color_tag="COLOR_03")
        layer_collection = create_or_get_collection(f"y{layer}", parent=units_collection)
        add_empty_cube(f"{row},{layer},{col}", location, scale, layer_collection)
