import bpy
import os
import re
import bpy.utils.previews
from .Functions import addon_prefs
from . import TMUnlimiter


PREVIEW_COLLECTIONS = {}
CACHED_TEXTURE_ITEMS = {}


def get_texture_dir_path(ty=None):
    ty = ty or bpy.context.scene.tm_material_type
    return getattr(addon_prefs(), f"{ty.lower()}_path")


def get_image_path(ty=None):
    ty = ty or bpy.context.scene.tm_material_type
    folder = get_texture_dir_path(ty)
    image_name = getattr(bpy.context.scene, f'tm_{ty.lower()}_texture')

    if not folder or not image_name:
        return ''

    return os.path.join(folder, image_name)


# Nom de la texture sans son extension, ex. "StadiumRoad.dds" -> "StadiumRoad"
def texture_name(img_path):
    return os.path.splitext(os.path.basename(img_path))[0]


def material_name(img_path):
    """Nom du material TrackMania (tel que dans tmunlimiter) correspondant à une texture,
    ex. "StadiumGrass1.dds" -> "StadiumGrass", "StadiumFabricD.dds" -> "StadiumFabric".
    Sinon le nom de la texture sans extension."""
    file_name = os.path.basename(img_path)
    base = texture_name(img_path)

    materials = TMUnlimiter.game_materials()
    if materials:
        known = {name.lower(): name for name, _textures in materials}
        users = {}
        for name, textures in materials:
            for texture in textures:
                users.setdefault(texture.lower(), set()).add(name)
    else:
        # tmunlimiter pas chargé : liste de l'Auto Mat
        from ..operators.OT_AutoMat import material_list
        known = {name.lower(): name for name in material_list}
        users = {}

    # Lettre du type de texture : Diffuse, Specular, Normal, Occlusion, Lightmap
    no_role = re.sub(r"(?<=[a-z0-9])_?[DSNOL]$", "", base)

    for candidate in (base, no_role):
        if candidate.lower() in known:
            return known[candidate.lower()]

    # Texture utilisée par un seul material dans tmunlimiter, ex. StadiumWarpStands3D -> StadiumControlStands3
    texture_users = users.get(file_name.lower(), ())
    if len(texture_users) == 1:
        return next(iter(texture_users))

    # Numéro de variante, ex. StadiumGrass1 -> StadiumGrass
    no_number = re.sub(r"\d+$", "", no_role)
    if no_number.lower() in known:
        return known[no_number.lower()]

    return base


# Refresh cached list of texture items
def refresh(ty=None):
    ty = ty or bpy.context.scene.tm_material_type
    folder = get_texture_dir_path(ty)

    items = []
    CACHED_TEXTURE_ITEMS[ty] = items

    for i, fn in enumerate(os.listdir(folder)):
        ident = fn
        name = fn
        description = ""
        icon = load_preview_icon(os.path.join(folder, fn), ty)
        items.append((ident, name, description, icon, i))


# Refresh a texture list if it's not in the cache
def auto_refresh(ty=None):
    ty = ty or bpy.context.scene.tm_material_type
    if ty in CACHED_TEXTURE_ITEMS:
        return
    try:
        refresh(ty)
    except Exception as e:
        pass


# Callback run when a texture path preference changed
def on_texture_path_changed(ty):
    global PREVIEW_COLLECTIONS
    global CACHED_TEXTURE_ITEMS

    CACHED_TEXTURE_ITEMS.pop(ty, None)
    if ty in PREVIEW_COLLECTIONS:
        bpy.utils.previews.remove(PREVIEW_COLLECTIONS[ty])
        del PREVIEW_COLLECTIONS[ty]


def fetch_texture_items(ty):
    items = CACHED_TEXTURE_ITEMS.get(ty, [])
    filter = bpy.context.scene.tm_texture_filter

    if filter:
        filter = filter.lower()
        items = [item for item in items if filter in item[0].lower()]

    return items


def fetch_texture_items_tmnf(self, context):
    return fetch_texture_items('TMNF')

def fetch_texture_items_tm2(self, context):
    return fetch_texture_items('TM2')

def fetch_texture_items_tm20(self, context):
    return fetch_texture_items('TM20')


def load_preview_icon(path, ty=None):
    ty = ty or bpy.context.scene.tm_material_type

    pcol = PREVIEW_COLLECTIONS.get(ty)
    if pcol is None:
        pcol = PREVIEW_COLLECTIONS[ty] = bpy.utils.previews.new()

    if not path in pcol:
        try:
            pcol.load(path, path, "IMAGE")
        except Exception:
            return 0

    return pcol[path].icon_id


def create_material(name):
    bpy.ops.object.material_slot_add('INVOKE_DEFAULT')

    material = bpy.data.materials.new(name=name)
    material.use_nodes = True

    slot_index = bpy.context.view_layer.objects.active.active_material_index
    bpy.context.active_object.material_slots[slot_index].material = material

    return material


def add_texture_to_material(material, img_path):
    node_tree = material.node_tree

    img_node = node_tree.nodes.new(type='ShaderNodeTexImage')
    img_node.image = bpy.data.images.load(
        filepath=img_path,
        check_existing=True,
    )

    for node in node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            node_tree.links.new(img_node.outputs['Color'], node.inputs['Base Color'])
            img_node.location = node.location[0] - 350, node.location[1] - 50
            break


def clear_cache():
    global PREVIEW_COLLECTIONS
    global CACHED_TEXTURE_ITEMS

    for pcol in PREVIEW_COLLECTIONS.values():
        bpy.utils.previews.remove(pcol)

    PREVIEW_COLLECTIONS = {}
    CACHED_TEXTURE_ITEMS = {}
