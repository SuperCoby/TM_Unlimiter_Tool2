import bpy
from ..utils.Functions import *
from ..operators.OT_Imports import TM_OT_ImportItem


class TM_PT_Imports(bpy.types.Panel):
    bl_label = "Import"
    locals().update( PANEL_CLASS_COMMON_DEFAULT_PROPS )
    bl_parent_id = "SNA_PT_main"
    bl_order = 60

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        row = box.row(align=True)
        row.scale_y = 1.5
        row.operator(TM_OT_ImportItem.bl_idname, text=".Item / .Solid / .Block.Gbx", icon=ICON_IMPORT)


classes = (
    TM_PT_Imports,
)
