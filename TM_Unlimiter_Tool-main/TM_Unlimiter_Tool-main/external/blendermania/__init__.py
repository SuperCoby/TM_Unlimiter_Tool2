import bpy
import os
from bpy.props import *

ADDON_ROOT_PATH = os.path.dirname(__file__)

from .operators.OT_Items_Icon import *
from .panels.PT_Items_Icon import *
from .properties.PannelsPropertyGroup import *


# register order matters for UI panel ordering
classes = (
    PannelsPropertyGroup,
    # icons,
    TM_PT_Items_Icon,
    TM_OT_Items_Icon_Test,
)


# register classes
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.tm_props = PointerProperty(type=PannelsPropertyGroup)


# delete classes
def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.tm_props
