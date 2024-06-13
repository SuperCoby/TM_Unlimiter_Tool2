import bpy
import os
from bpy.types import Operator, Panel
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper

# Opérateur personnalisé pour ouvrir le sélecteur de fichiers
class OBJECT_OT_open_filebrowser(Operator, ImportHelper):
    bl_idname = "object.open_filebrowser"
    bl_label = "Open File Browser"
    bl_options = {'REGISTER', 'UNDO'}
    bl_category = "TM"
    bl_context = "objectmode"
    bl_parent_id = "SNA_PT_main"

    # Filtre de fichier (ici on peut spécifier les extensions, par exemple: "*.png;*.jpg;*.jpeg")
    filter_glob: StringProperty(default="*.*", options={'HIDDEN'})

    target_prop: StringProperty(default="", options={'HIDDEN'})

    def execute(self, context):
        bpy.context.object.unlimiter_object_settings.texture_props.texture_type = 'Custom'
        # Extraire le chemin du fichier à partir du répertoire "Data"
        data_dir = os.path.join(os.path.basename(os.path.dirname(self.filepath)), os.path.basename(self.filepath))
        # Mettre à jour le chemin du fichier dans la propriété souhaitée
        if self.target_prop == "diffuse_filepath":
            context.object.unlimiter_object_settings.texture_props.texture_custom.diffuse.filepath = data_dir
        elif self.target_prop == "specular_filepath":
            context.object.unlimiter_object_settings.texture_props.texture_custom.specular.filepath = data_dir
        elif self.target_prop == "normal_filepath":
            context.object.unlimiter_object_settings.texture_props.texture_custom.normal.filepath = data_dir
        elif self.target_prop == "lighting_filepath":
            context.object.unlimiter_object_settings.texture_props.texture_custom.lighting.filepath = data_dir
        elif self.target_prop == "occlusion_filepath":
            context.object.unlimiter_object_settings.texture_props.texture_custom.occlusion.filepath = data_dir
        # Forcer le rafraîchissement de l'interface utilisateur
        context.area.tag_redraw()
        # Forcer un rafraîchissement global de l'interface utilisateur
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        return {'FINISHED'}


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


def register():
    bpy.utils.register_class(OBJECT_OT_open_filebrowser)
    bpy.utils.register_class(VIEW3D_PT_texture_custom)
    bpy.types.Object.show_diffuse = BoolProperty(default=True)
    bpy.types.Object.show_specular = BoolProperty(default=True)
    bpy.types.Object.show_normal = BoolProperty(default=True)
    bpy.types.Object.show_lighting = BoolProperty(default=True)
    bpy.types.Object.show_occlusion = BoolProperty(default=True)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_open_filebrowser)
    bpy.utils.unregister_class(VIEW3D_PT_texture_custom)
    del bpy.types.Object.show_diffuse
    del bpy.types.Object.show_specular
    del bpy.types.Object.show_normal
    del bpy.types.Object.show_lighting
    del bpy.types.Object.show_occlusion

if __name__ == "__main__":
    register()
