import bpy
from ..utils.TMUnlimiter import has_material_collision


# Opérateur pour ouvrir les propriétés de collision (comme l'original)
class TMU_OT_collision_properties(bpy.types.Operator):
    bl_idname = "wm.tmu_collision_properties"
    bl_label = "TM: Collision Properties"
    bl_description = "Open collision properties for the active object material"

    @classmethod
    def poll(cls, context):
        if not has_material_collision():
            cls.poll_message_set("Requires the TrackMania Unlimiter: Custom Block exporter addon")
            return False
        return True

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout

        if context.active_object and context.active_object.active_material:
            material = context.active_object.active_material
            data = material.unlimiter_material_collision

            layout.label(text=f"Material: {material.name}", icon='MATERIAL')
            layout.separator()

            layout.prop(data, "is_collidable")

            if data.is_collidable:
                layout.prop(data, "collision_material")
        else:
            layout.label(text="No active object or material selected", icon='ERROR')


classes = (
    TMU_OT_collision_properties,
)
