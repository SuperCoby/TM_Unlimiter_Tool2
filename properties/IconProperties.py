import bpy
import bpy.utils.previews
from bpy.props import *

from ..utils.Descriptions import *
from .IconFunctions import *

# ? CB = CheckBox => BoolProperty
# ? LI = List     => EnumProperty
# ? NU = Number   => IntProperty, FloatProperty
# ? ST = String   => StringProperty


class TMU_PannelsPropertyGroup(bpy.types.PropertyGroup):
    """general trackmania properties"""

    CB_showConvertPanel: BoolProperty(default=False, update=redraw_panels)

    # icons
    CB_icon_overwriteIcons: BoolProperty(
        name="Overwrite Icons", default=True, update=redraw_panels
    )
    LI_icon_perspective: EnumProperty(items=getIconPerspectives(), name="Perspective")
    LI_icon_world: EnumProperty(items=getIconWorlds(), name="World", default="STANDARD")
    # Fond transparent (pas de background) ; appliqué à scene.render.film_transparent au rendu
    CB_icon_transparentBG: BoolProperty(
        name="No Background", default=True, update=redraw_panels
    )
    NU_icon_padding: IntProperty(
        min=0, max=100, default=80, subtype="PERCENTAGE", update=redraw_panels
    )
    NU_icon_bgColor: FloatVectorProperty(
        name="BG Color",
        subtype="COLOR",
        min=0,
        max=1,
        size=4,
        default=(1, 1, 1, 1),
        update=updateWorldBG,
    )
    # obsolete
    CB_icon_genIcons: BoolProperty(
        name="Generate Icons", default=True, update=redraw_panels
    )


class TMU_InvalidMaterial(bpy.types.PropertyGroup):
    material: PointerProperty(type=bpy.types.Material)


classes = (
    TMU_PannelsPropertyGroup,
)


def register():
    bpy.types.Scene.tmu_icon_props = PointerProperty(type=TMU_PannelsPropertyGroup)


def unregister():
    del bpy.types.Scene.tmu_icon_props
