bl_info = {
    "name": "TM_Unlimiter_Tool",
    "author": "Coby",
    "description": "",
    "blender": (5, 1, 1),
    "version": (1, 1, 0),
    "location": "",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "category": "3D View",
}


import bpy

# Le plus tôt possible : avant que tmunlimiter_blender_plugin fasse `import lzo`
from .utils import LzoShim
LzoShim.install()

from .properties import (
    Preferences,
    MaterialsProperties,
    IconProperties,
    ToolsProperties,
    DetectionProperties,
    CustomTextureProperties,
    BlockAnimationProperties,
)
from .operators import (
    OT_Imports,
    OT_Items_Edges_Import,
    OT_Materials,
    OT_Tools,
    OT_Items_Icon,
    OT_Tool2,
    OT_Detection,
    OT_CustomTexture,
    OT_CollisionHeader,
    OT_BlockDefinitions,
    OT_DebugUnlimiter,
    OT_AutoMat,
    OT_Separate,
    OT_Collision,
    OT_BlockAnimation,
)
from .panels import (
    PT_main,
    PT_Imports,
    PT_Materials,
    PT_Items_Icon,
    PT_Tool2,
    PT_Detection,
    PT_CustomTexture,
    PT_BlockAnimation,
    PT_CollisionHeader,
    PT_DebugUnlimiter,
)
from .utils import TMUnlimiterPatches


# Chaque module peut définir :
#   classes      : tuple de classes bpy.types, enregistrées dans l'ordre
#   register()   : le reste (propriétés de Scene/Object, menus, timers...), appelé après ses classes
#   unregister() : l'inverse, appelé avant de désenregistrer ses classes
# L'ordre compte : propriétés avant opérateurs/panneaux, PT_main avant les autres panneaux
# (ils s'y rattachent via bl_parent_id), et l'ordre des panneaux = ordre d'affichage.
modules = (
    Preferences,
    MaterialsProperties,
    IconProperties,
    ToolsProperties,
    DetectionProperties,
    CustomTextureProperties,
    BlockAnimationProperties,

    OT_Imports,
    OT_Items_Edges_Import,
    OT_Materials,
    OT_Tools,
    OT_Items_Icon,
    OT_Tool2,
    OT_Detection,
    OT_CustomTexture,
    OT_CollisionHeader,
    OT_BlockDefinitions,
    OT_DebugUnlimiter,
    OT_AutoMat,
    OT_Separate,
    OT_Collision,
    OT_BlockAnimation,

    PT_main,
    PT_Imports,
    PT_Materials,
    PT_Items_Icon,
    PT_Tool2,
    PT_Detection,
    PT_CustomTexture,
    PT_BlockAnimation,
    PT_CollisionHeader,
    PT_DebugUnlimiter,

    TMUnlimiterPatches,
)


def register():
    LzoShim.install()

    for mod in modules:
        for cls in getattr(mod, "classes", ()):
            bpy.utils.register_class(cls)
        if hasattr(mod, "register"):
            mod.register()


def unregister():
    for mod in reversed(modules):
        if hasattr(mod, "unregister"):
            mod.unregister()
        for cls in reversed(getattr(mod, "classes", ())):
            # Déjà retirée (ex. l'ancien script tm_block_animation.py lancé à côté a les mêmes classes)
            if getattr(cls, "is_registered", False):
                bpy.utils.unregister_class(cls)

    LzoShim.uninstall()
