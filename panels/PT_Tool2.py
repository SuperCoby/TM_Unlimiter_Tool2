import bpy


class OBJECT_PT_MyPanel(bpy.types.Panel):
    bl_label = "Tool 2.0"
    bl_idname = "OBJECT_PT_MyPanel"
    bl_space_type = "VIEW_3D"
    bl_parent_id = "SNA_PT_main"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}
    bl_category = "Tools"
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        manual_auto = context.scene.tmu_manual_auto_menu

        layout.prop(context.scene, "tmu_manual_auto_menu", expand=True)

        if manual_auto == "Auto":
            col = layout.column(align=True)
            col.operator("object.duplicate_and_merge", text="Collision")
            col.operator("object.my_operator_separate_2", text="Separate+Modifier+Occ")
            col.operator("object.automat", text="Game material")
        else:
            # Ajouter un bouton "Separate + Modifiers" dans le panneau
            layout.operator("object.my_operator_separate", text="Separate + Modifiers")
            layout.operator("object.merge_operator", text="Merge Material")
            layout.separator()

            # Créer une boîte pour les options UV
            box = layout.box()
            box.label(text="Add Occ")
            box.prop(context.scene, "uv_option", text="")
            box.operator("object.add_uv_operator", text="Exécuter")

            # Créer une deuxième boîte pour les options de lumière
            box = layout.box()
            box.label(text="Add Fake Light")
            box.prop(context.scene, "uv_option_2", text="")
            box.operator("object.add_uv_operator_2", text="Exécuter")


classes = (
    OBJECT_PT_MyPanel,
)
