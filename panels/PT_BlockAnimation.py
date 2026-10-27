import bpy
from ..utils import BlockAnimation as block_anim
from ..utils import TMUnlimiter as tmu
from ..operators import OT_BlockAnimation


class TMBLOCKANIM_PT_panel(bpy.types.Panel):
    bl_label = "Block Animation"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "TM"
    bl_parent_id = "SNA_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type in {"MESH", "EMPTY", "LIGHT"}

    def draw(self, context):
        layout = self.layout
        obj = context.object
        settings = obj.tm_block_animation
        anim = block_anim.analyse(obj, context.scene)

        if tmu.module("plug_tree") is None:
            layout.label(text="tmunlimiter_blender_plugin not loaded", icon="ERROR")

        box = layout.box()

        # In the block: visual only
        row = box.row(align=True)
        row.prop(settings, "enabled", text="")
        row.label(text="In the block (fake collision)", icon="MESH_CUBE")
        if settings.enabled and anim is not None:
            # Only mention what would prevent the export
            if "error" in anim:
                box.label(text=anim["error"], icon="ERROR")
            for warning in anim["warnings"]:
                box.label(text=warning, icon="ERROR")

        # In the map: visual + collision
        row = box.row(align=True)
        row.prop(settings, "use_map", text="")
        row.label(text="In the map + collision", icon="WORLD")
        if settings.use_map:
            name = block_anim.block_identifier_for(obj, context.scene)
            box.prop(settings, "map_path", text="")
            box.operator(OT_BlockAnimation.TMBLOCKANIM_OT_read_map.bl_idname, icon="FILE_REFRESH")

            path = bpy.path.abspath(settings.map_path)
            if path and settings.list_source == block_anim.list_source(path, name):
                if not settings.instances:
                    box.label(text=f"\"{name}\" not in the map", icon="ERROR")
                    box.label(text=f"Blocks found: {settings.map_blocks or 'none'}", icon="BLANK1")
                col = box.column(align=True)
                for item in settings.instances:
                    row = col.row(align=True)
                    row.prop(item, "selected", text="")
                    row.label(text=f"{name}  ({item.x}, {item.y}, {item.z})",
                              icon="KEYFRAME_HLT" if item.animated else "KEYFRAME")
                box.prop(settings, "backup")
                row = box.row()
                row.scale_y = 1.4
                row.enabled = any(item.selected for item in settings.instances)
                row.operator(OT_BlockAnimation.TMBLOCKANIM_OT_write_map.bl_idname, text="Write to map", icon="EXPORT")


classes = (
    TMBLOCKANIM_PT_panel,
)
