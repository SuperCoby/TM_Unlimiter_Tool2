import bpy
from bpy.props import EnumProperty, StringProperty
from ..utils.TextureCache import (
    fetch_texture_items_tmnf,
    fetch_texture_items_tm2,
    fetch_texture_items_tm20,
)


scene_props = (
    ("tm_material_type", EnumProperty(
        name='TrackMania Material Type',
        items=[
            ('TMNF', 'TMNF', 'TrackMania Nations Forever'),
            ('TM2', 'TM²', 'TrackMania²'),
            ('TM20', 'TM20', 'TrackMania 2020'),
        ],
    )),
    ("tm_tmnf_texture", EnumProperty(
        name='TMNF Texture',
        items=fetch_texture_items_tmnf,
    )),
    ("tm_tm2_texture", EnumProperty(
        name='TM² Texture',
        items=fetch_texture_items_tm2,
    )),
    ("tm_tm20_texture", EnumProperty(
        name='TM20 Texture',
        items=fetch_texture_items_tm20,
    )),
    ("tm_texture_filter", StringProperty(
        name='Filter',
        description='Filter textures by names'
    )),
)


def register():
    for prop_name, prop_value in scene_props:
        setattr(bpy.types.Scene, prop_name, prop_value)


def unregister():
    for prop_name, _ in scene_props:
        delattr(bpy.types.Scene, prop_name)
