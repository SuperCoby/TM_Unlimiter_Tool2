import bpy
from ..utils import DebugUnlimiter as dbg


def draw_debug_button(self, context):
    # Rapport basé sur les propriétés de tmunlimiter_blender_plugin : rien à afficher sans lui
    if not hasattr(bpy.types.Material, "unlimiter_material_collision") and dbg.handler is None:
        return

    layout = self.layout
    layout.separator()
    
    row = layout.row()
    
    if dbg.handler is not None:
        row.alert = True
        op = row.operator("view3d.tmu_toggle_debug", text="Debug ON", icon="HIDE_OFF", emboss=True)
    else:
        op = row.operator("view3d.tmu_toggle_debug", text="Debug OFF", icon="HIDE_ON", emboss=True)


def register():
    bpy.types.VIEW3D_MT_editor_menus.append(draw_debug_button)


def unregister():
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_debug_button)
