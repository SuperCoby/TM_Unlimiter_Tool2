import bpy
from bpy.types import Panel
from ..utils.TMUnlimiter import tmunlimiter_enabled


# Panneau personnalisé pour ajouter le bouton
class VIEW3D_PT_texture_custom(Panel):
    bl_idname = "VIEW3D_PT_texture_custom"
    bl_label = "Custom Texture"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TM" 
    bl_context = "objectmode" 
    bl_options = {"DEFAULT_CLOSED"} 
    bl_parent_id = "SNA_PT_main"

    @classmethod
    def poll(cls, context):
        return tmunlimiter_enabled()

    def draw(self, context):
        layout = self.layout
        obj = context.object

        if obj:
            if hasattr(obj, "unlimiter_object_settings"):
                # Ajouter une propriété booléenne pour contrôler la visibilité de Diffuse, Specular, Normal, Lighting et Occlusion
                row = layout.row(align=True)
                row.prop(obj.unlimiter_object_settings.texture_props.texture_custom, "use_diffuse", text="D")
                row.prop(obj.unlimiter_object_settings.texture_props.texture_custom, "use_specular", text="S")        
                row.prop(obj.unlimiter_object_settings.texture_props.texture_custom, "use_normal", text="N")
                row.prop(obj.unlimiter_object_settings.texture_props.texture_custom, "use_lighting", text="L")
                row.prop(obj.unlimiter_object_settings.texture_props.texture_custom, "use_occlusion", text="O")

                # Afficher les éléments Diffuse si la case est cochée
                if obj.unlimiter_object_settings.texture_props.texture_custom.use_diffuse:
                    row = layout.row(align=True)
                    row.prop(obj.unlimiter_object_settings.texture_props.texture_custom.diffuse, "filepath", text="Diffuse")
                    row.operator("object.open_filebrowser", text="", icon='FILEBROWSER').target_prop = "diffuse_filepath"

                # Afficher les éléments Specular si la case est cochée
                if obj.unlimiter_object_settings.texture_props.texture_custom.use_specular:
                    row = layout.row(align=True)
                    row.prop(obj.unlimiter_object_settings.texture_props.texture_custom.specular, "filepath", text="Specular")
                    row.operator("object.open_filebrowser", text="", icon='FILEBROWSER').target_prop = "specular_filepath"

                # Afficher les éléments Normal si la case est cochée
                if obj.unlimiter_object_settings.texture_props.texture_custom.use_normal:
                    row = layout.row(align=True)
                    row.prop(obj.unlimiter_object_settings.texture_props.texture_custom.normal, "filepath", text="Normal")
                    row.operator("object.open_filebrowser", text="", icon='FILEBROWSER').target_prop = "normal_filepath"

                # Afficher les éléments Lighting si la case est cochée
                if obj.unlimiter_object_settings.texture_props.texture_custom.use_lighting:
                    row = layout.row(align=True)
                    row.prop(obj.unlimiter_object_settings.texture_props.texture_custom.lighting, "filepath", text="Lighting")
                    row.operator("object.open_filebrowser", text="", icon='FILEBROWSER').target_prop = "lighting_filepath"

                # Afficher les éléments Occlusion si la case est cochée
                if obj.unlimiter_object_settings.texture_props.texture_custom.use_occlusion:
                    row = layout.row(align=True)
                    row.prop(obj.unlimiter_object_settings.texture_props.texture_custom.occlusion, "filepath", text="Occlusion")
                    row.operator("object.open_filebrowser", text="", icon='FILEBROWSER').target_prop = "occlusion_filepath"


classes = (
    VIEW3D_PT_texture_custom,
)
