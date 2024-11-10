import bpy

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
                if num_faces > 6:
                    intersecting_empty_objects.append(empty_obj)
            
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

def create_or_get_collection(name, parent=None, color_tag=None):
    collection = bpy.data.collections.get(name)
    if not collection:
        collection = bpy.data.collections.new(name)
        if parent:
            parent.children.link(collection)
        else:
            bpy.context.scene.collection.children.link(collection)
    if color_tag:
        collection.color_tag = color_tag
    return collection

def add_empty_cube(name, location, scale, collection):
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = 'CUBE'
    empty.location = location
    empty.scale = scale
    collection.objects.link(empty)

def add_multiple_empties(start_location, scale, rows, columns, step_x, step_y, collection, z_position, step_z):
    for row in range(rows):
        for col in range(columns):
            name = f"{row},{z_position},{col}"
            location = (
                start_location[0] + col * step_x, 
                start_location[1] + row * step_y, 
                start_location[2] + z_position * step_z
            )
            add_empty_cube(name, location, scale, collection)

def setup_block_units(rows, columns, start_location, scale, step_x, step_y, step_z, parent_collection, num_collections, z_offset_increment):
    for i in range(num_collections):
        collection_name = f"y{i}"
        z_offset = i * z_offset_increment
        start_location_z = start_location[2] + (z_offset * step_z)
        collection = create_or_get_collection(collection_name, parent=parent_collection)
        add_multiple_empties(
            start_location=(start_location[0], start_location[1], start_location_z), 
            scale=scale,
            rows=rows,
            columns=columns,
            step_x=step_x,
            step_y=step_y,
            collection=collection,
            z_position=z_offset,
            step_z=step_z
        )

class BlockUnitPanel(bpy.types.Panel):
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
        
        # Ajout des paramètres d'unités de blocs
        box = layout.box()
        box.label(text="Block Units Parameters")
        
        row = box.row()
        row.prop(scene, "block_units_environment", text="")
        
        row = layout.row()
        row.prop(scene, "block_units_rows", text="Y")
        row.prop(scene, "block_units_columns", text="X")
        row.prop(scene, "block_units_z", text="Z")
        
        box.operator("object.create_block_units", text="Import")
        
        # Ajout du bouton Hide Non-Selected
        layout.prop(scene.apv_settings, 'hide_non_selected', text="Hide Non-Selected")
        
        # Le reste de ton code pour les objets vides
        row = layout.row()
        layout.operator('sna.intersectingemptyobjects_50398', text='Detected Objects', icon_value=0, emboss=True, depress=False,)

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


class CreateBlockUnitsOperator(bpy.types.Operator):
    bl_idname = "object.create_block_units"
    bl_label = "Create Block Units"

    def execute(self, context):
        scene = context.scene
        environment = scene.block_units_environment

        if environment in ['RALLY', 'BAY', 'STADIUM']:
            start_location = (16, 16, 4)
            scale = (16, 16, 4)
            step_x = 32
            step_y = 32
            step_z = 4
        elif environment == 'COAST':
            start_location = (8, 8, 2)
            scale = (8, 8, 2)
            step_x = 16
            step_y = 16
            step_z = 2
        elif environment == 'ISLAND':
            start_location = (32, 32, 1)
            scale = (32, 32, 1)
            step_x = 64
            step_y = 64
            step_z = 1
        elif environment in ['SNOW', 'DESERT']:
            start_location = (16, 16, 8)
            scale = (16, 16, 8)
            step_x = 32
            step_y = 32
            step_z = 8
        else:
            start_location = (16, 16, 4)
            scale = (16, 16, 4)
            step_x = 32
            step_y = 32
            step_z = 4

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

# Define the custom property for the "Hide Non-Selected" toggle
class APVSettings(bpy.types.PropertyGroup):
    hide_non_selected: bpy.props.BoolProperty(
        name="Hide Non-Selected",
        description="Hide objects that are not selected",
        default=False,
        update=lambda self, context: self.toggle_hide_non_selected(context)
    )
    
    def toggle_hide_non_selected(self, context):
        # Cacher/afficher les objets non sélectionnés
        for obj in context.scene.objects:
            if obj.type == 'EMPTY':
                if self.hide_non_selected and not obj.select_get():
                    obj.hide_set(True)
                else:
                    obj.hide_set(False)

class SNA_OT_DetectedObjects(bpy.types.Operator):
    bl_idname = "sna.detectedobjects_50398"
    bl_label = "Detected Objects"
    bl_description = "Detect and list selected empty objects"
    bl_options = {"REGISTER", "UNDO"}
    bl_category = "Tools"

    @classmethod
    def poll(cls, context):
        if bpy.app.version >= (3, 0, 0):
            cls.poll_message_set('')
        return not False

    def execute(self, context):
        selected_empty_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'EMPTY' and obj.select_get()]
        
        if not selected_empty_objects:
            self.report({'INFO'}, "No empty objects selected")
            return {"CANCELLED"}
        
        print("Detected Empty Objects:")
        for obj in selected_empty_objects:
            print(f"Detected object: {obj.name} at {obj.location}")

        for obj in selected_empty_objects:
            obj.location.x += 1
        
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selected_empty_objects:
            obj.select_set(True)
        
        self.report({'INFO'}, f"{len(selected_empty_objects)} empty object(s) detected")
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


def register():
    bpy.utils.register_class(BlockUnitPanel)
    bpy.utils.register_class(CreateBlockUnitsOperator)
    bpy.utils.register_class(APVSettings)
    bpy.utils.register_class(SNA_OT_Intersectingemptyobjects_50398)
    bpy.utils.register_class(SNA_OT_DetectedObjects)
    
    bpy.types.Scene.block_units_rows = bpy.props.IntProperty(
        name="Rows", default=10, min=1
    )
    bpy.types.Scene.block_units_columns = bpy.props.IntProperty(
        name="Columns", default=10, min=1
    )
    bpy.types.Scene.block_units_z = bpy.props.IntProperty(
        name="Z collections", default=10, min=1
    )
    bpy.types.Scene.block_units_environment = bpy.props.EnumProperty(
        name="Environment",
        items=[('STADIUM', "Stadium", "Stadium environment"),
               ('BAY', "Bay", "Bay environment"),
               ('COAST', "Coast", "Coast environment"),
               ('SNOW', "Snow", "Snow environment"),
               ('DESERT', "Desert", "Desert environment"),
               ('RALLY', "Rally", "Rally environment"),
               ('ISLAND', "Island", "Island environment")],
        default='STADIUM'
    )

    bpy.types.Scene.apv_settings = bpy.props.PointerProperty(type=APVSettings)

def unregister():
    bpy.utils.unregister_class(BlockUnitPanel)
    bpy.utils.unregister_class(CreateBlockUnitsOperator)
    bpy.utils.unregister_class(APVSettings)
    bpy.utils.unregister_class(SNA_OT_Intersectingemptyobjects_50398)
    bpy.utils.unregister_class(SNA_OT_DetectedObjects)
    
    del bpy.types.Scene.block_units_rows
    del bpy.types.Scene.block_units_columns
    del bpy.types.Scene.block_units_z
    del bpy.types.Scene.block_units_environment
    del bpy.types.Scene.apv_settings
