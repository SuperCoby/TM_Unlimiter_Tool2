import bpy
from ..utils.TextureCache import (
    get_texture_dir_path,
    get_image_path,
    material_name,
    refresh,
    create_material,
    add_texture_to_material,
    clear_cache,
)


# Refresh cached list of textures.
class SNA_OT_Refresh(bpy.types.Operator):
    bl_idname = "sna.refresh"
    bl_label = "Refresh"
    bl_description = "Refresh TM texture list"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        if not get_texture_dir_path():
            cls.poll_message_set('No texture path set')
            return False

        return True

    def execute(self, context):
        try:
            refresh()
            return {"FINISHED"}
        except Exception as e:
            print(e)
            self.report({'ERROR'}, "Couldn't load textures; check path")
            return {"CANCELLED"}


class SNA_OT_AddTexture(bpy.types.Operator):
    bl_idname = "sna.add_texture"
    bl_label = "Add Texture"
    bl_description = "Add texture to current material"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if not bpy.context.object:
            cls.poll_message_set('No active object')
            return False

        if (
            not bpy.context.object.active_material or
            not bpy.context.object.active_material.node_tree
        ):
            cls.poll_message_set('No active material to add to')
            return False

        return True

    def execute(self, context):
        img_path = get_image_path()
        if not img_path:
            return {'CANCELLED'}

        material = bpy.context.object.active_material
        add_texture_to_material(material, img_path)
        material.name = material_name(img_path)
        return {"FINISHED"}


class SNA_OT_AddTextureMaterial(bpy.types.Operator):
    bl_idname = "sna.add_texture_material"
    bl_label = "Add Texture Material"
    bl_description = "Create new material with current texture"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if not bpy.context.object:
            cls.poll_message_set('No active object')
            return False

        return True

    def execute(self, context):
        img_path = get_image_path()
        if not img_path:
            return {'CANCELLED'}

        mat = create_material(material_name(img_path))
        add_texture_to_material(mat, img_path)
        return {"FINISHED"}


classes = (
    SNA_OT_Refresh,
    SNA_OT_AddTexture,
    SNA_OT_AddTextureMaterial,
)


def unregister():
    clear_cache()
