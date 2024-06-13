from bpy.types import (
    Panel,
)

from ..utils.Functions import *
from ..utils.Constants import *
from ..properties.Functions import *


class TM_PT_Items_Icon(Panel):
    # region bl_
    """Creates a Panel in the Object properties window"""
    bl_label = "Render Icon"
    bl_idname = "TM_PT_Items_Icon"
    bl_parent_id = "SNA_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}
    # endregion

    @classmethod
    def poll(cls, context):
        return not is_convert_panel_active()

    def draw_header(self, context):
        layout = self.layout
        tm_props = get_global_props()
        row = layout.row()
        row.enabled = tm_props.CB_icon_overwriteIcons

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        tm_props = scene.tm_props
        useTransparentBG = scene.render.film_transparent

        layout.enabled = tm_props.CB_icon_overwriteIcons

        row = layout.row()
        row.prop(tm_props, "LI_icon_perspective", text="Cam")

        row = layout.row()
        row.prop(tm_props, "NU_icon_padding", text="Fill space", expand=True)

        row = layout.row(align=True)
        row2 = row.row(align=True)
        row2.label(text="Bground")

        row2 = row.row(align=True)
        row2.prop(
            scene.render,
            "film_transparent",
            text="None",
            toggle=True,
            icon="GHOST_DISABLED",
        )

        row3 = row.row(align=True)
        row3.enabled = (
            True
            if not useTransparentBG and tm_props.LI_icon_world == "STANDARD"
            else False
        )
        row3.prop(tm_props, "NU_icon_bgColor", text="")

        row = layout.row(align=True)
        row2 = row.row(align=True)
        row2.label(text="Size")

        row2 = row.row(align=True)
        row2.prop(tm_props, "LI_icon_pxDimension", expand=True)

        layout.separator(factor=UI_SPACER_FACTOR)

        row = layout.row()
        row.scale_y = 1
        row.operator(
            "view3d.tm_make_test_icon", text="Do a test render", icon=ICON_ICON
        )
