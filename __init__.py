bl_info = {
    "name": "TM_Unlimiter_Tool",
    "author": "Coby",
    "description": "",
    "blender": (3, 0, 0),
    "version": (1, 0, 0),
    "location": "",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "category": "3D View",
}


import bpy
import os


ADDON_ROOT_PATH = os.path.dirname(__file__)


def addon_prefs():
    return bpy.context.preferences.addons[__package__].preferences


#

from .operators.OT_Materials import on_texture_path_changed


def on_tmnf_path_changed(self, context):
    on_texture_path_changed("TMNF")


def on_tm2_path_changed(self, context):
    on_texture_path_changed("TM2")


def on_tm20_path_changed(self, context):
    on_texture_path_changed("TM20")


class SNA_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

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

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "tmnf_path")
        layout.prop(self, "tm2_path")
        layout.prop(self, "tm20_path")



from .operators import OT_Imports
from .operators import OT_Items_Edges_Import
from .operators import OT_Materials
from .operators import OT_Tools
from .operators.AutoMat import register_automat, unregister_automat
from .operators.Col import register_col, unregister_col
from .operators.Separate import register_separate, unregister_separate
from .panels import PT_Imports
from .panels import PT_main
from .panels import PT_Materials
from .panels import PT_Tools
from .external import register_external, unregister_external


modules = (
    # Must come first so others can parent to it
    PT_main,
    OT_Imports,
    OT_Items_Edges_Import,
    OT_Materials,
    OT_Tools,
    PT_Imports,
    PT_Materials,
    PT_Tools,
)


def register():
    bpy.utils.register_class(SNA_AddonPreferences)

    for mod in modules:
        if hasattr(mod, "classes"):
            for cls in mod.classes:
                bpy.utils.register_class(cls)
        if hasattr(mod, "scene_props"):
            for prop_name, prop_value in mod.scene_props:
                setattr(bpy.types.Scene, prop_name, prop_value)
        if hasattr(mod, "register"):
            mod.register()
    register_external()

    register_automat()
    register_separate()
    register_col()



def unregister():
    unregister_automat()
    unregister_separate()
    unregister_col()

    unregister_external()

    for mod in modules:
        if hasattr(mod, "unregister"):
            mod.unregister()
        if hasattr(mod, "scene_props"):
            for prop_name, _ in mod.scene_props:
                delattr(bpy.types.Scene, prop_name)
        if hasattr(mod, "classes"):
            for cls in mod.classes:
                bpy.utils.unregister_class(cls)

    bpy.utils.unregister_class(SNA_AddonPreferences)
