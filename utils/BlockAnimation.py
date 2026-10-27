import bpy
import functools
import math
import mathutils
import os
import struct
import sys

# Animation des blocks TMUnlimiter (d'après tm_block_animation.py de SuperCoby) :
# 1) "In the block" : à l'export de tmunlimiter_blender_plugin, ajoute à chaque objet animé le
#    chunk 0x0904F011 (FuncTree) de son CPlugTree, vers un CFuncTreeRotate ou un CFuncTreeTranslate
#    (greffé par utils/TMUnlimiterPatches.py avec wrap_plug_tree_animation). Classes de TmForever.exe
#    (lecteurs natifs vérifiés dans le code décompilé) :
#      CFuncPlug          0x0500B004 : Period, Phase, AutoCreateMotion, RandomizePhase
#      CFuncTreeRotate    0x0501E001 : Axis (vec3), AngleMin, AngleMax
#      CFuncTreeTranslate 0x0500D000 : StartPoint (vec3), EndPoint (vec3)
#    Le jeu ne boucle qu'entre 2 valeurs : seules la première et la dernière keyframe comptent.
# 2) "In the map + collision" : écrit un Block Motion TMUnlimiter sur les blocks placés dans une map.

CHUNK_TREE_LOCATION = 0x0904F01A
CHUNK_TREE_FUNC = 0x0904F011
FACADE = 0xFACADE01
# End of a CPlugTree written by plug_tree_from_object: 0x0904F01A + flags + 12 floats + facade
TREE_TAIL_SIZE = 4 + 4 + 12 * 4 + 4


# --- Reading the Blender animation -----------------------------------------------------------

def _fcurves(obj):
    anim_data = obj.animation_data
    if anim_data is None or anim_data.action is None:
        return []
    action = anim_data.action
    try:
        # Blender 4.4+: slotted actions, Action.fcurves no longer exists in 5.x
        from bpy_extras import anim_utils
        channelbag = anim_utils.action_get_channelbag_for_slot(action, anim_data.action_slot)
        return list(channelbag.fcurves) if channelbag else []
    except (ImportError, AttributeError):
        return list(getattr(action, "fcurves", []))


def analyse(obj, scene):
    """None if the object has no exportable animation, else a dict; "error" if it is invalid."""
    curves = {"location": {}, "rotation_euler": {}}
    for fcurve in _fcurves(obj):
        if fcurve.data_path in curves and not fcurve.mute:
            curves[fcurve.data_path][fcurve.array_index] = fcurve

    used = [fc for group in curves.values() for fc in group.values() if len(fc.keyframe_points)]
    if not used:
        return None

    frames = [key.co.x for fc in used for key in fc.keyframe_points]
    start, end = min(frames), max(frames)
    if end <= start:
        return None

    def sample(path, default, frame):
        return [curves[path][i].evaluate(frame) if i in curves[path] else default[i] for i in range(3)]

    loc_start = sample("location", obj.location, start)
    loc_end = sample("location", obj.location, end)
    rot_start = sample("rotation_euler", obj.rotation_euler, start)
    rot_end = sample("rotation_euler", obj.rotation_euler, end)

    moves = any(abs(loc_end[i] - loc_start[i]) > 1e-5 for i in range(3))
    rot_axes = [i for i in range(3) if abs(rot_end[i] - rot_start[i]) > 1e-6]

    fps = scene.render.fps / scene.render.fps_base
    anim = {
        "start": start,
        "end": end,
        "period": (end - start) / fps,
        "loc_start": loc_start,
        "loc_end": loc_end,
        "rot_start": rot_start,
        "rot_end": rot_end,
        "warnings": [],
    }

    if moves and rot_axes:
        anim["error"] = "Rotation AND translation: only one per object (put the other on a parent Empty)"
    elif len(rot_axes) > 1:
        anim["error"] = "Rotation on several axes: the game only rotates on one axis"
    elif rot_axes:
        anim["type"] = "ROTATE"
        anim["axis"] = rot_axes[0]
    elif moves:
        anim["type"] = "TRANSLATE"
    else:
        return None

    if obj.rotation_mode in {"QUATERNION", "AXIS_ANGLE"}:
        anim["warnings"].append("Non-Euler rotation mode: the exporter reads rotation_euler")
    if any(len(fc.keyframe_points) > 2 for fc in used):
        anim["warnings"].append("In-between keyframes ignored (only the first and last count)")
    return anim


# --- GBX writing -----------------------------------------------------------------------------

def _to_game(vec):
    # Same axis conversion as plug_tree.py: Blender (x, y, z) -> game (y, z, x)
    return (vec[1], vec[2], vec[0])


def _write_func_plug(gbx, period):
    gbx.nat32(0x0500B004)
    gbx.real(period)
    gbx.real(0.0)  # Phase
    gbx.nat32(1)  # AutoCreateMotion: the engine creates the Motion that runs the function itself
    gbx.nat32(0)  # RandomizePhase


def func_tree(gbx, anim):
    # Absolute keyframe values (checked in game: the game replaces the pose)
    if anim["type"] == "ROTATE":
        axis = anim["axis"]
        axis_vec = [0.0, 0.0, 0.0]
        axis_vec[axis] = 1.0

        gbx.nat32(0x0501E000)
        _write_func_plug(gbx, anim["period"])
        gbx.nat32(0x0501E001)
        for value in _to_game(axis_vec):
            gbx.real(value)
        gbx.real(anim["rot_start"][axis])  # AngleMin
        gbx.real(anim["rot_end"][axis])  # AngleMax
    else:
        gbx.nat32(0x0500D000)
        _write_func_plug(gbx, anim["period"])
        gbx.nat32(0x0500D000)
        for value in _to_game(anim["loc_start"]) + _to_game(anim["loc_end"]):
            gbx.real(value)

    gbx.nat32(FACADE)


def _insert_func_tree(gbx, obj, anim):
    # plug_tree_from_object writes 0x0904F01A then facade last: 0x0904F011 is slipped in just before
    buffer = gbx.buffer
    data = buffer.getvalue()
    tail = data[-TREE_TAIL_SIZE:]
    if (len(data) < TREE_TAIL_SIZE
            or int.from_bytes(tail[0:4], "little") != CHUNK_TREE_LOCATION
            or int.from_bytes(tail[-4:], "little") != FACADE):
        print(f'[TM Block Animation] "{obj.name}": unexpected CPlugTree end, animation not written')
        return

    buffer.seek(len(data) - TREE_TAIL_SIZE)
    buffer.truncate()
    gbx.nat32(CHUNK_TREE_FUNC)
    gbx.mw_ref(func_tree, anim)
    gbx.buffer.write(tail)
    print(f'[TM Block Animation] "{obj.name}": {anim["type"]} exported ({anim["period"]:.3f} s)')


def wrap_plug_tree_animation(original):
    @functools.wraps(original)  # keeps __name__: mw_ref() uses it for the validators
    def plug_tree_from_object(gbx, object, *args, **kwargs):
        settings = getattr(object, "tm_block_animation", None)
        anim = None
        if settings is not None and settings.enabled:
            anim = analyse(object, bpy.context.scene)
            if anim is not None and "error" in anim:
                print(f'[TM Block Animation] "{object.name}": {anim["error"]}')
                anim = None
        if anim is None:
            return original(gbx, object, *args, **kwargs)

        # Exported static pose = first keyframe, whatever the current frame
        saved_location = object.location.copy()
        saved_rotation = object.rotation_euler.copy()
        object.location = anim["loc_start"]
        object.rotation_euler = anim["rot_start"]
        try:
            result = original(gbx, object, *args, **kwargs)
        finally:
            object.location = saved_location
            object.rotation_euler = saved_rotation

        _insert_func_tree(gbx, object, anim)
        return result
    return plug_tree_from_object


# --- TMUnlimiter Block Motion (in the map) ---------------------------------------------------
# The FuncTree above only animates the visual: the block's collision stays still. TMUnlimiter's
# Block Motion moves the whole block (visual + collision), but it is stored per placed block in
# the map, in private chunk 0x3F001003 (format decoded from test maps):
#   per block: u8 kind (0 Nadeo, 2 custom), Id name, Id collection/author, 3 x u32 coord,
#              u8 direction, u32 native flags, u16 TMUnlimiter flags, then depending on them:
#              0x01 Block Offset vec3, 0x02/0x04 vec3, 0x08 Block Motion, 0x10 Block Origin vec3
#              (rotation pivot, minus the pivot position), 0x20 groups, 0x600==0x200 6 floats
#   Block Motion: u8 (bits 0-2 wave type, bit 3 manual control), u32 count,
#                 28-byte keyframes: u32 time (ms), vec3 position, vec3 rotation (degrees)
#   0x40 = "Is Dynamic", required for the Block Motion to play

MOTION_CHUNK = 0x3F001003
FLAG_MOTION = 0x08
FLAG_ORIGIN = 0x10
FLAG_DYNAMIC = 0x40
WAVE_TYPE = 3  # default value of TMUnlimiter's Block Motion editor


class MapError(Exception):
    pass


class _Reader:
    def __init__(self, data, pos=0):
        self.data = data
        self.pos = pos

    def take(self, size):
        if self.pos + size > len(self.data):
            raise MapError("unexpected end of data")
        chunk = self.data[self.pos:self.pos + size]
        self.pos += size
        return chunk

    def u8(self):
        return self.take(1)[0]

    def u16(self):
        return int.from_bytes(self.take(2), "little")

    def u32(self):
        return int.from_bytes(self.take(4), "little")


def _lzo():
    lzo = sys.modules.get("lzo")
    if lzo is None:
        raise MapError('"lzo" module missing (it is provided by TM_Unlimiter_Tool)')
    return lzo


def read_gbx(path):
    """(start of the file up to the body, decompressed body)"""
    data = open(path, "rb").read()
    r = _Reader(data)
    if r.take(3) != b"GBX" or r.u16() != 6:
        raise MapError("not a version 6 GBX file")
    r.take(4)  # "BUCR" format
    r.u32()  # class
    r.take(r.u32())  # user data
    r.u32()  # node count
    external_count = r.u32()
    if external_count:
        r.u32()  # ancestor level

        def folders():
            for _ in range(r.u32()):
                r.take(r.u32())
                folders()
        folders()
        for _ in range(external_count):
            flags = r.u32()
            if flags & 4:
                r.u32()
            else:
                r.take(r.u32())
            r.u32()
            r.u32()
            if not flags & 4:
                r.u32()
    head = data[:r.pos]
    size = r.u32()
    compressed = r.take(r.u32())
    return head, bytes(_lzo().decompress(compressed, False, size))


def write_gbx(path, head, body):
    compressed = bytes(_lzo().compress(body, 1, False))
    with open(path, "wb") as file:
        file.write(head)
        file.write(len(body).to_bytes(4, "little"))
        file.write(len(compressed).to_bytes(4, "little"))
        file.write(compressed)


def _count_ids_before(body, end):
    # The body's Ids share a single table: count the strings declared before the chunk
    count = 0
    pos = 0
    while True:
        pos = body.find(b"\x00\x00\x00", pos, end)
        if pos < 0 or pos + 8 > end:
            return count
        if body[pos + 3] in (0x40, 0x80):
            size = int.from_bytes(body[pos + 4:pos + 8], "little")
            text = body[pos + 8:pos + 8 + size]
            # Printable text, line breaks included (sentinel block "TMUnlimiter ... is required")
            if 0 < size < 4096 and len(text) == size and all(c >= 32 or c in (9, 10, 13) for c in text):
                count += 1
                pos += 8 + size
                continue
        pos += 1


class _IdTable:
    def __init__(self, known):
        self.known = known
        self.names = {}

    def read(self, r):
        value = r.u32()
        if value == 0xFFFFFFFF:
            return ""
        if value & 0xC0000000 and value & 0x3FFFFFFF == 0:
            name = r.take(r.u32()).decode("latin-1")
            self.known += 1
            self.names[self.known] = name
            return name
        return self.names.get(value & 0x3FFFFFFF)  # None: declared outside the chunk


def _parse_motion_blocks(chunk, start, count, ids):
    r = _Reader(chunk, start)
    blocks = []
    for _ in range(count):
        kind = r.u8()
        if kind not in (0, 2, 3):
            raise MapError(f"unsupported entry kind {kind}")
        name = ids.read(r)
        author = ids.read(r)
        coord = struct.unpack("<3I", r.take(12))
        r.take(1 + 4)  # direction, native flags
        flags_pos = r.pos
        flags = r.u16()
        for bit in (0x01, 0x02, 0x04):
            if flags & bit:
                r.take(12)
        motion_start = r.pos
        if flags & FLAG_MOTION:
            if not r.u8() & 8:
                r.take(28 * r.u32())
        motion_end = r.pos
        if flags & FLAG_ORIGIN:
            r.take(12)
        origin_end = r.pos
        if flags & 0x20:
            r.take(4 * r.u32())
        if flags & 0x600 == 0x200:
            r.take(24)
        blocks.append({"kind": kind, "name": name, "author": author, "coord": coord, "flags": flags,
                       "flags_pos": flags_pos, "motion": (motion_start, motion_end),
                       "origin": (motion_end, origin_end)})
    return blocks, r.pos


def find_motion_chunk(body):
    marker = MOTION_CHUNK.to_bytes(4, "little") + b"PIKS"
    pos = body.find(marker)
    if pos < 0:
        raise MapError("TMUnlimiter chunk 0x3F001003 not found (map without TMUnlimiter?)")
    size = int.from_bytes(body[pos + 8:pos + 12], "little")
    chunk = body[pos + 12:pos + 12 + size]
    known = _count_ids_before(body, pos)
    # The chunk header varies with its version: take the block count position for which every
    # entry parses and ends exactly at the end of the chunk
    for start in range(0, min(len(chunk) - 4, 128)):
        count = int.from_bytes(chunk[start:start + 4], "little")
        if not 0 < count < 100000:
            continue
        try:
            blocks, end = _parse_motion_blocks(chunk, start + 4, count, _IdTable(known))
        except (MapError, UnicodeDecodeError):
            continue
        if end == len(chunk):
            return pos, chunk, blocks
    raise MapError("unrecognized 0x3F001003 chunk structure")


def encode_motion(keyframes, wave_type):
    data = bytes([wave_type & 7]) + len(keyframes).to_bytes(4, "little")
    for time_ms, position, rotation in keyframes:
        data += int(round(time_ms)).to_bytes(4, "little")
        data += struct.pack("<6f", *position, *rotation)
    return data


def list_block_instances(path, block_name):
    """([(coord, already animated)] of the instances of custom block "block_name" in map order,
    names of all custom blocks in the map)"""
    _, body = read_gbx(path)
    blocks = [b for b in find_motion_chunk(body)[2] if b["kind"] != 0]
    instances = [(b["coord"], bool(b["flags"] & FLAG_MOTION)) for b in blocks if b["name"] == block_name]
    return instances, sorted({b["name"] or "?" for b in blocks})


def apply_motion_to_map(path, block_name, keyframes, wave_type, backup=True, only=None, origin=None):
    """Writes the Block Motion onto the custom blocks "block_name" of the map (only = {(rank, coord)}
    to target some of them, rank = position among the instances; origin = Block Origin vec3 to set).
    Returns how many."""
    head, body = read_gbx(path)
    chunk_pos, chunk, blocks = find_motion_chunk(body)
    motion = encode_motion(keyframes, wave_type)

    instances = [b for b in blocks if b["kind"] != 0 and b["name"] == block_name]
    if not instances:
        names = sorted({b["name"] or "?" for b in blocks if b["kind"] != 0})
        raise MapError(f'no custom block "{block_name}" in the map (found: {", ".join(names) or "none"})')
    if only is not None:
        current = {(rank, b["coord"]) for rank, b in enumerate(instances)}
        if not only <= current:
            raise MapError("the map changed since it was read: click \"Read map\" again")
        instances = [b for rank, b in enumerate(instances) if (rank, b["coord"]) in only]

    patched = bytearray(chunk)
    count = 0
    # From the end to the start: positions of earlier entries stay valid
    for block in reversed(instances):
        flags = block["flags"] | FLAG_MOTION | FLAG_DYNAMIC
        # Block Origin first: it comes after the motion, so the motion span stays valid
        if origin is not None:
            start, end = block["origin"]
            patched[start:end] = struct.pack("<3f", *origin)
            flags |= FLAG_ORIGIN
        start, end = block["motion"]
        patched[start:end] = motion
        patched[block["flags_pos"]:block["flags_pos"] + 2] = flags.to_bytes(2, "little")
        count += 1
    if not count:
        raise MapError("no instance checked")

    new_body = (body[:chunk_pos + 8] + len(patched).to_bytes(4, "little") + bytes(patched)
                + body[chunk_pos + 12 + len(chunk):])
    if backup:
        import shutil
        shutil.copyfile(path, path + ".bak")
    write_gbx(path, head, new_body)
    return count


def motion_keyframes(obj, scene):
    """Blender keyframes -> Block Motion keyframes, relative to the first keyframe (implicit at t=0)."""
    curves = {"location": {}, "rotation_euler": {}}
    for fcurve in _fcurves(obj):
        if fcurve.data_path in curves and not fcurve.mute:
            curves[fcurve.data_path][fcurve.array_index] = fcurve
    frames = sorted({key.co.x for group in curves.values() for fc in group.values() for key in fc.keyframe_points})
    if len(frames) < 2:
        return []

    def sample(path, default, frame):
        return [curves[path][i].evaluate(frame) if i in curves[path] else default[i] for i in range(3)]

    fps = scene.render.fps / scene.render.fps_base
    start = frames[0]
    loc0 = sample("location", obj.location, start)
    rot0 = sample("rotation_euler", obj.rotation_euler, start)
    keyframes = []
    for frame in frames[1:]:
        loc = sample("location", obj.location, frame)
        rot = sample("rotation_euler", obj.rotation_euler, frame)
        position = _to_game([loc[i] - loc0[i] for i in range(3)])
        rotation = _to_game([math.degrees(rot[i] - rot0[i]) for i in range(3)])
        keyframes.append(((frame - start) / fps * 1000.0, position, rotation))
    return keyframes


def block_origin_for(obj, scene):
    """Block Origin making TMUnlimiter rotate the block around the object's origin, as in Blender:
    minus the pivot position (object origin at the first keyframe) in game axes. A pivot at the
    centre of a 32 x 32 block gives (-16, _, -16), the value found in the game."""
    curves = {fc.array_index: fc for fc in _fcurves(obj) if fc.data_path == "location" and not fc.mute}
    frames = [key.co.x for fc in _fcurves(obj) for key in fc.keyframe_points]
    start = min(frames) if frames else scene.frame_current
    pivot = mathutils.Vector([curves[i].evaluate(start) if i in curves else obj.location[i] for i in range(3)])
    if obj.parent is not None:
        pivot = obj.parent.matrix_world @ obj.matrix_parent_inverse @ pivot
    return tuple(-v for v in _to_game(pivot))


def block_identifier_for(obj, scene):
    # Identifier of the TMUnlimiter block definition one of whose variations has this object
    # (or a parent) as its model; otherwise, the object's name (without a .001 suffix)
    chain = []
    current = obj
    while current is not None:
        chain.append(current)
        current = current.parent
    for block_def in getattr(scene, "tmunlimiter_block_definitions", []):
        for variants_name in [p for p in block_def.bl_rna.properties.keys() if p.startswith("variants_")]:
            variants = getattr(block_def, variants_name)
            for variation in list(variants.ground_variations) + list(variants.air_variations):
                if variation.model in chain:
                    return block_def.identifier
    name = obj.name
    if len(name) > 4 and name[-4] == "." and name[-3:].isdigit():
        name = name[:-4]
    return name


def list_source(path, name):
    return f"{os.path.normcase(os.path.abspath(path))}|{name}"


def fill_instances(settings, path, name):
    # Keep the boxes already checked when the same map is read again
    previous = {(item.rank, item.x, item.y, item.z): item.selected for item in settings.instances}
    same_source = settings.list_source == list_source(path, name)
    settings.instances.clear()
    instances, map_blocks = list_block_instances(path, name)
    settings.map_blocks = ", ".join(map_blocks)
    for rank, (coord, animated) in enumerate(instances):
        item = settings.instances.add()
        item.rank = rank
        item.x, item.y, item.z = coord
        item.animated = animated
        item.selected = previous.get((rank, *coord), True) if same_source else True
    settings.list_source = list_source(path, name)
