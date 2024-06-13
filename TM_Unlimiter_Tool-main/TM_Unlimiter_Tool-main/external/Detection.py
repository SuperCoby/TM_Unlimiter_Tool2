import bpy
from os import path

class SNA_OT_Intersectingemptyobjects_50398(bpy.types.Operator):
    bl_idname = "sna.intersectingemptyobjects_50398"
    bl_label = "IntersectingEmptyObjects"
    bl_description = ""
    bl_options = {"REGISTER", "UNDO"}
    bl_category = "Tools"

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0) and True:
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        # Function to create a cube at the origin of an empty object and adjust its dimensions
        def create_cube_from_empty(empty_obj):
            # Create a new cube mesh
            bpy.ops.mesh.primitive_cube_add(location=empty_obj.location)
            cube_obj = bpy.context.active_object
            # Adjust the dimensions of the cube based on the scale of the empty object
            scale_x, scale_y, scale_z = empty_obj.scale
            cube_obj.scale[0] *= scale_x * 0.98  # Adjust scale to 0.98
            cube_obj.scale[1] *= scale_y * 0.98
            cube_obj.scale[2] *= scale_z * 0.98
            return cube_obj
        
        # Function to apply boolean modifier to a cube
        def apply_boolean_modifier(cube_obj, selected_mesh_obj):
            # Add boolean difference modifier to the cube
            bool_mod = cube_obj.modifiers.new(name="Boolean", type='BOOLEAN')
            bool_mod.operation = 'DIFFERENCE'
            bool_mod.object = selected_mesh_obj
        
        # Get the selected mesh object
        selected_mesh_obj = bpy.context.active_object
        
        # Check if the selected object is a mesh object
        if selected_mesh_obj.type != 'MESH':
            print("Selected object is not a mesh object.")
        else:
            # Get all empty objects in the scene
            empty_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'EMPTY']
            
            # List to store intersecting empty objects
            intersecting_empty_objects = []
            
            # List to store created cubes
            created_cubes = []
            
            # Create cubes and adjust their positions
            for empty_obj in empty_objects:
                cube_obj = create_cube_from_empty(empty_obj)
                created_cubes.append(cube_obj)
                
                # Add boolean modifier to the cube
                apply_boolean_modifier(cube_obj, selected_mesh_obj)
            
            # Move selected object, empty objects, and cubes -1 unit in the x-axis
            for obj in [selected_mesh_obj] + empty_objects + created_cubes:
                obj.location.x -= 1
            
            # Apply all boolean modifiers
            bpy.ops.object.select_all(action='DESELECT')
            for obj in bpy.context.scene.objects:
                if obj.type == 'MESH':
                    bpy.context.view_layer.objects.active = obj
                    bpy.ops.object.modifier_apply(modifier="Boolean")
            
            # Check the number of faces of each cube
            for empty_obj, cube_obj in zip(empty_objects, created_cubes):
                num_faces = len(cube_obj.data.polygons)
                print("Number of faces of cube at empty object", empty_obj.name, ":", num_faces)
                if num_faces > 6:
                    intersecting_empty_objects.append(empty_obj)
            
            # Print intersecting empty objects
            print("Intersecting empty objects:", intersecting_empty_objects)
            
            # Select intersecting empty objects
            bpy.ops.object.select_all(action='DESELECT')
            for obj in intersecting_empty_objects:
                obj.select_set(True)
            
            # Move selected object, empty objects, and cubes 1 unit in the x-axis
            for obj in [selected_mesh_obj] + empty_objects + created_cubes:
                obj.location.x += 1
            
            # Remove the cubes
            for cube_obj in created_cubes:
                bpy.data.objects.remove(cube_obj, do_unlink=True)
        
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


class VIEW3D_PT_CustomPanel(bpy.types.Panel):
    bl_label = "Detection Units"
    bl_idname = "VIEW3D_PT_custom_panel"
    bl_space_type = "VIEW_3D"
    bl_parent_id = "SNA_PT_main"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}
    bl_category = "Tools"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
                 
        layout.prop(scene.apv_settings, 'hide_non_selected', text="Hide Non-Selected")
       
        row = layout.row()
        from .. import ADDON_ROOT_PATH
        op = row.operator(OBJECT_OT_ImportCollection.bl_idname, text="Import Blockunits")
        op.filepath = path.join(ADDON_ROOT_PATH, "assets", "Block_units", "blockunits.blend") + rf"\Collection\\"
        op.filename = "blockunits"

        # Ajout du bouton "Run"
        layout.operator('sna.intersectingemptyobjects_50398', text='Detected Objects', icon_value=0, emboss=True, depress=False)

        box = layout.box()
        box.label(text="")
        names = sorted([obj.name for obj in context.scene.objects if obj.select_get() and (obj.type == 'EMPTY')])
        num_names = len(names)
        rows = (num_names + 2) // 3  # Calculate number of rows needed, rounding up
        flow = box.grid_flow(row_major=True, columns=3, even_columns=True, even_rows=False, align=True)
        for i in range(rows):
            for j in range(3):
                index = i * 3 + j
                if index < num_names:
                    flow.label(text=names[index])


class APVSettings(bpy.types.PropertyGroup):
    hide_non_selected: bpy.props.BoolProperty(
        name="Hide Non-Selected Objects",
        description="Toggle visibility of non-selected objects in the viewport",
        default=False,
        update=lambda self, context: update_visibility(context)
    )

def update_visibility(context):
    settings = context.scene.apv_settings
    for obj in context.scene.objects:
        if obj.type == 'EMPTY' and not obj.select_get():
            obj.hide_set(settings.hide_non_selected)


class OBJECT_OT_ImportCollection(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.import_collection"
    bl_label = "Append Collection"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filename: bpy.props.StringProperty()

    def execute(self, context):
        abs_path = path.abspath(self.filepath)
        bpy.ops.wm.append(filename=self.filename, directory=abs_path)
        return {'FINISHED'}




def register():
    bpy.utils.register_class(SNA_OT_Intersectingemptyobjects_50398)
    bpy.utils.register_class(VIEW3D_PT_CustomPanel)
    bpy.utils.register_class(APVSettings)
    bpy.types.Scene.apv_settings = bpy.props.PointerProperty(type=APVSettings)
    bpy.utils.register_class(OBJECT_OT_ImportCollection)
    # bpy.utils.register_class(ImportBlendPanel)


def unregister():
    bpy.utils.unregister_class(SNA_OT_Intersectingemptyobjects_50398)
    bpy.utils.unregister_class(VIEW3D_PT_CustomPanel)
    bpy.utils.unregister_class(APVSettings)
    del bpy.types.Scene.apv_settings
    bpy.utils.unregister_class(OBJECT_OT_ImportCollection)
    # bpy.utils.unregister_class(ImportBlendPanel)


if __name__ == "__main__":
    register()
