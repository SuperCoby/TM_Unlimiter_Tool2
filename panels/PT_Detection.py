import bpy


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


classes = (
    BlockUnitPanel,
)
