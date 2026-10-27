import bpy


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


classes = (
    APVSettings,
)


def register():
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
    del bpy.types.Scene.block_units_rows
    del bpy.types.Scene.block_units_columns
    del bpy.types.Scene.block_units_z
    del bpy.types.Scene.block_units_environment
    del bpy.types.Scene.apv_settings
