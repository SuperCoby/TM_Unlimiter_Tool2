import bpy
from ..utils.TMUnlimiter import has_material_collision

# Contrôles de collision dans l'en-tête de la 3D View.
# Les propriétés `material.unlimiter_material_collision` viennent de l'addon
# tmunlimiter_blender_plugin (Tomek0055) : s'il n'est pas installé/activé, rien n'est affiché.


# Ajoute directement les contrôles à l'en-tête de la 3D View
def draw_collision_header(self, context):
    if not has_material_collision():
        return

    layout = self.layout
    layout.separator()

    if context.active_object and context.active_object.active_material:
        data = context.active_object.active_material.unlimiter_material_collision

        # Checkbox "Is collidable" directement dans la barre
        layout.prop(data, "is_collidable", text="Collidable")

        # Si collidable, afficher le dropdown du matériau de collision
        if data.is_collidable:
            layout.prop(data, "collision_material", text="")
    else:
        layout.label(text="No Material", icon='QUESTION')


def register():
    bpy.types.VIEW3D_MT_editor_menus.append(draw_collision_header)


def unregister():
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_collision_header)
