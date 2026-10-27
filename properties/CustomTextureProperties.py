import bpy
from bpy.props import BoolProperty


def register():
    bpy.types.Object.show_diffuse = BoolProperty(default=True)
    bpy.types.Object.show_specular = BoolProperty(default=True)
    bpy.types.Object.show_normal = BoolProperty(default=True)
    bpy.types.Object.show_lighting = BoolProperty(default=True)
    bpy.types.Object.show_occlusion = BoolProperty(default=True)


def unregister():
    del bpy.types.Object.show_diffuse
    del bpy.types.Object.show_specular
    del bpy.types.Object.show_normal
    del bpy.types.Object.show_lighting
    del bpy.types.Object.show_occlusion
