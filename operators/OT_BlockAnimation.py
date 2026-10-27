import bpy
import os
from ..utils import BlockAnimation as anim


class TMBLOCKANIM_OT_write_map(bpy.types.Operator):
    """Writes this object's keyframes as a TMUnlimiter Block Motion onto its blocks placed in the map"""
    bl_idname = "object.tmblockanim_write_map"
    bl_label = "Write animation to map"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        obj = context.object
        settings = obj.tm_block_animation
        path = bpy.path.abspath(settings.map_path)
        name = anim.block_identifier_for(obj, context.scene)
        keyframes = anim.motion_keyframes(obj, context.scene)
        if not keyframes:
            self.report({"ERROR"}, "At least 2 keyframes are needed (location / rotation_euler)")
            return {"CANCELLED"}
        if not path or not os.path.isfile(path):
            self.report({"ERROR"}, "Choose a .Challenge.Gbx map")
            return {"CANCELLED"}
        if settings.list_source != anim.list_source(path, name):
            self.report({"ERROR"}, "Click \"Read map\" first")
            return {"CANCELLED"}
        only = {(item.rank, (item.x, item.y, item.z)) for item in settings.instances if item.selected}
        try:
            count = anim.apply_motion_to_map(path, name, keyframes, anim.WAVE_TYPE, backup=settings.backup, only=only,
                                        origin=anim.block_origin_for(obj, context.scene))
            anim.fill_instances(settings, path, name)
        except anim.MapError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        backup = ", backup: .bak" if settings.backup else ""
        self.report({"INFO"}, f'Block Motion written on {count} block(s) "{name}" ({len(keyframes)} keyframe(s)){backup}')
        print(f'[TM Block Animation] {path}: {count} block(s) "{name}", keyframes {keyframes}')
        return {"FINISHED"}


class TMBLOCKANIM_OT_read_map(bpy.types.Operator):
    """Reads the map and lists the instances of this block placed in it"""
    bl_idname = "object.tmblockanim_read_map"
    bl_label = "Read map"

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def execute(self, context):
        obj = context.object
        settings = obj.tm_block_animation
        path = bpy.path.abspath(settings.map_path)
        if not path or not os.path.isfile(path):
            self.report({"ERROR"}, "Choose a .Challenge.Gbx map")
            return {"CANCELLED"}
        try:
            anim.fill_instances(settings, path, anim.block_identifier_for(obj, context.scene))
        except anim.MapError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


classes = (
    TMBLOCKANIM_OT_write_map,
    TMBLOCKANIM_OT_read_map,
)
