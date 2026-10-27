import bpy
import os
from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper
from ..utils.TMUnlimiter import tmunlimiter_enabled


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

    @classmethod
    def poll(cls, context):
        return tmunlimiter_enabled() and context.object is not None

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


classes = (
    OBJECT_OT_open_filebrowser,
)
