import bpy
from ..utils.Detection import (
    detect_block_units,
    grid_settings,
    create_or_get_collection,
    setup_block_units,
)


class SNA_OT_Intersectingemptyobjects_50398(bpy.types.Operator):
    bl_idname = "sna.intersectingemptyobjects_50398"
    bl_label = "Detected Objects"
    bl_description = "Select the cube empties (block units) occupied by the selected mesh(es)"
    bl_options = {"REGISTER", "UNDO"}

    margin: bpy.props.FloatProperty(
        name="Margin",
        description="Shrink each block unit by this distance, to ignore geometry that only "
                    "slightly pokes into a neighbouring unit",
        default=0.0, min=0.0, soft_max=1.0, unit='LENGTH',
    )

    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not meshes and context.active_object and context.active_object.type == 'MESH':
            meshes = [context.active_object]
        if not meshes:
            self.report({'ERROR'}, "Select at least one mesh object")
            return {"CANCELLED"}

        empties = [obj for obj in context.scene.objects
                   if obj.type == 'EMPTY' and obj.empty_display_type == 'CUBE']
        if not empties:
            self.report({'ERROR'}, "No cube empties (block units) in the scene")
            return {"CANCELLED"}

        hit = detect_block_units(meshes, empties, context.evaluated_depsgraph_get(), self.margin)

        hide = context.scene.apv_settings.hide_non_selected
        for obj in context.selected_objects:
            obj.select_set(False)
        for empty in empties:
            if hide:
                empty.hide_set(False)
        for empty in hit:
            empty.select_set(True)
        if hide:
            context.scene.apv_settings.toggle_hide_non_selected(context)

        self.report({'INFO'}, f"{len(hit)} block unit(s) detected")
        return {"FINISHED"}


class CreateBlockUnitsOperator(bpy.types.Operator):
    bl_idname = "object.create_block_units"
    bl_label = "Create Block Units"

    def execute(self, context):
        scene = context.scene
        start_location, scale, step_x, step_y, step_z = grid_settings(scene.block_units_environment)

        rows = scene.block_units_rows
        columns = scene.block_units_columns
        z = scene.block_units_z
        block_units_collection = create_or_get_collection("BlockUnits", color_tag='COLOR_03')

        setup_block_units(
            rows=rows, 
            columns=columns, 
            start_location=start_location, 
            scale=scale, 
            step_x=step_x, 
            step_y=step_y, 
            step_z=step_z, 
            parent_collection=block_units_collection, 
            num_collections=z,  
            z_offset_increment=1
        )

        return {'FINISHED'}


classes = (
    CreateBlockUnitsOperator,
    SNA_OT_Intersectingemptyobjects_50398,
)
