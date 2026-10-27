import bpy
from ..utils.Functions import ADDON_ID
from ..utils.TextureCache import on_texture_path_changed


def on_tmnf_path_changed(self, context):
    on_texture_path_changed("TMNF")


def on_tm2_path_changed(self, context):
    on_texture_path_changed("TM2")


def on_tm20_path_changed(self, context):
    on_texture_path_changed("TM20")


class SNA_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    tmnf_path: bpy.props.StringProperty(
        name="TMNF Textures",
        subtype="FILE_PATH",
        update=on_tmnf_path_changed,
    )

    tm2_path: bpy.props.StringProperty(
        name="TM² Textures",
        subtype="FILE_PATH",
        update=on_tm2_path_changed,
    )

    tm20_path: bpy.props.StringProperty(
        name="TM20 Textures",
        subtype="FILE_PATH",
        update=on_tm20_path_changed,
    )

    block_author: bpy.props.StringProperty(
        name="Block Author",
        description="Author written in block definitions created by Auto Block Definition (TMUnlimiter)",
        default="SuperCoby",
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "tmnf_path")
        layout.prop(self, "tm2_path")
        layout.prop(self, "tm20_path")
        layout.separator()
        layout.prop(self, "block_author")


classes = (
    SNA_AddonPreferences,
)
