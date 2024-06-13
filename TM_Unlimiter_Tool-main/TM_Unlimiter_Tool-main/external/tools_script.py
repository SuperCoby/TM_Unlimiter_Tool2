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
        manual_auto = context.scene.manual_auto_menu

        layout.prop(context.scene, "manual_auto_menu", expand=True)

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


class OBJECT_OT_MyOperatorSeparate(bpy.types.Operator):
    bl_idname = "object.my_operator_separate"
    bl_label = "Separate + Modifiers"

    def execute(self, context):
        # Votre code pour "Separate + Modifiers" ici
        if bpy.context.selected_objects:
            objet_selectionne = bpy.context.selected_objects[0]
            if objet_selectionne.type == "MESH":
                # Ajoute le modificateur "Edge Split" à l'objet de base
                bpy.context.view_layer.objects.active = objet_selectionne

                # Vérifie si le modificateur "Edge Split" existe déjà
                edge_split_modifier = None
                for modifier in objet_selectionne.modifiers:
                    if modifier.type == "EDGE_SPLIT":
                        edge_split_modifier = modifier

                if edge_split_modifier is None:
                    edge_split_modifier = objet_selectionne.modifiers.new(
                        name="EdgeSplit", type="EDGE_SPLIT"
                    )
                    edge_split_modifier.split_angle = 30

                # Sépare l'objet en fonction des matériaux
                bpy.ops.object.mode_set(mode="EDIT")
                bpy.ops.mesh.separate(type="MATERIAL")
                bpy.ops.object.mode_set(mode="OBJECT")

                # Parente les nouveaux objets
                nouveaux_objets = bpy.context.selected_objects
                parent = objet_selectionne
                for nouvel_objet in nouveaux_objets:
                    if nouvel_objet != objet_selectionne:
                        nouvel_objet.parent = parent
                        parent = nouvel_objet

                print(
                    "Tous les objets ont été créés avec succès et parentés de manière hiérarchique à l'objet initial."
                )
            else:
                print("L'objet sélectionné n'est pas un objet de type MESH.")
        else:
            print("Aucun objet sélectionné.")

        return {"FINISHED"}


class OBJECT_OT_MergeOperator(bpy.types.Operator):
    bl_idname = "object.merge_operator"
    bl_label = "Merge"

    def execute(self, context):
        def merge_materials():
            all_materials = bpy.data.materials
            existing_materials = {}

            for material in all_materials:
                base_name = material.name.split('.')[0]

                if '.' not in material.name and base_name not in existing_materials:
                    existing_materials[base_name] = material

            for material in all_materials:
                if '.' in material.name:
                    base_name = material.name.split('.')[0]
                    if base_name in existing_materials:
                        for obj in bpy.data.objects:
                            for slot in obj.material_slots:
                                if slot.material == material:
                                    slot.material = existing_materials[base_name]
                        bpy.data.materials.remove(material)

            print("Materials merged successfully.")

        # Appeler la fonction pour fusionner les matériaux
        merge_materials()
        return {'FINISHED'}


class OBJECT_OT_AddUVOperator(bpy.types.Operator):
    bl_idname = "object.add_uv_operator"
    bl_label = "Add UV"

    def execute(self, context):
        # Votre code pour "Add UV" ici
        if bpy.context.active_object:
            obj = bpy.context.active_object
            if len(obj.data.uv_layers) < 2:
                # Obtenez la valeur de l'option sélectionnée
                selected_option = bpy.context.scene.uv_option

                # Créez le nouveau UV Map en fonction de l'option sélectionnée
                new_uv_map = obj.data.uv_layers.new(name=f"{selected_option}")
                print(
                    f"UV Map '{new_uv_map.name}' créé avec succès dans les données de l'objet."
                )

                # Modifier les coordonnées UV en fonction de l'option sélectionnée
                # StadiumRoadO
                if selected_option == "SROMap":
                    old_uv_map = obj.data.uv_layers.active
                    for face in obj.data.polygons:
                        for loop_index in face.loop_indices:
                            vertex_index = obj.data.loops[loop_index].vertex_index
                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                            # Ajuster les coordonnées des sommets UV
                            new_uv = (
                                (old_uv.x * 0.001) + 0.3,
                                (old_uv.y * 0.001) + 0.8,
                            )  # Modifier l'échelle et la position
                            obj.data.uv_layers[new_uv_map.name].data[
                                loop_index
                            ].uv = new_uv
                    print(
                        "Les coordonnées UV des sommets ont été ajustées avec succès."
                    )

                # StadiumRoadO2
                elif selected_option == "SRO2Map":
                    old_uv_map = obj.data.uv_layers.active
                    for face in obj.data.polygons:
                        for loop_index in face.loop_indices:
                            vertex_index = obj.data.loops[loop_index].vertex_index
                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                            # Ajuster les coordonnées des sommets UV
                            new_uv = (
                                (old_uv.x * 0.001) + 0.3,
                                (old_uv.y * 0.001) + 0.8,
                            )  # Modifier l'échelle et la position
                            obj.data.uv_layers[new_uv_map.name].data[
                                loop_index
                            ].uv = new_uv
                    print(
                        "Les coordonnées UV des sommets ont été ajustées avec succès."
                    )

                    # StadiumWarpO
                elif selected_option == "SWOmap":
                    old_uv_map = obj.data.uv_layers.active
                    for face in obj.data.polygons:
                        for loop_index in face.loop_indices:
                            vertex_index = obj.data.loops[loop_index].vertex_index
                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                            # Ajuster les coordonnées des sommets UV
                            new_uv = (
                                (old_uv.x * 0.001) + 0.33,
                                (old_uv.y * 0.001) + 0.09,
                            )  # Modifier l'échelle et la position
                            obj.data.uv_layers[new_uv_map.name].data[
                                loop_index
                            ].uv = new_uv
                    print(
                        "Les coordonnées UV des sommets ont été ajustées avec succès."
                    )

                # StadiumWarpO2
                elif selected_option == "SWO2Map":
                    old_uv_map = obj.data.uv_layers.active
                    for face in obj.data.polygons:
                        for loop_index in face.loop_indices:
                            vertex_index = obj.data.loops[loop_index].vertex_index
                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                            # Ajuster les coordonnées des sommets UV
                            new_uv = (
                                (old_uv.x * 0.001) + 0.01,
                                (old_uv.y * 0.001) + 0.98,
                            )  # Modifier l'échelle et la position
                            obj.data.uv_layers[new_uv_map.name].data[
                                loop_index
                            ].uv = new_uv
                    print(
                        "Les coordonnées UV des sommets ont été ajustées avec succès."
                    )

                    # StadiumGrassO
                elif selected_option == "SGOMap":
                    old_uv_map = obj.data.uv_layers.active
                    for face in obj.data.polygons:
                        for loop_index in face.loop_indices:
                            vertex_index = obj.data.loops[loop_index].vertex_index
                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                            # Ajuster les coordonnées des sommets UV
                            new_uv = (
                                (old_uv.x * 0.001) + 0.21,
                                (old_uv.y * 0.001) + 0.6,
                            )  # Modifier l'échelle et la position
                            obj.data.uv_layers[new_uv_map.name].data[
                                loop_index
                            ].uv = new_uv
                    print(
                        "Les coordonnées UV des sommets ont été ajustées avec succès."
                    )

                    # StadiumFabricO
                elif selected_option == "SFOMap":
                    old_uv_map = obj.data.uv_layers.active
                    for face in obj.data.polygons:
                        for loop_index in face.loop_indices:
                            vertex_index = obj.data.loops[loop_index].vertex_index
                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                            # Ajuster les coordonnées des sommets UV
                            new_uv = (
                                (old_uv.x * 0.001) + 0.52,
                                (old_uv.y * 0.001) + 0.82,
                            )  # Modifier l'échelle et la position
                            obj.data.uv_layers[new_uv_map.name].data[
                                loop_index
                            ].uv = new_uv
                    print(
                        "Les coordonnées UV des sommets ont été ajustées avec succès."
                    )

                    # StadiumControlO
                elif selected_option == "SCOMap":
                    old_uv_map = obj.data.uv_layers.active
                    for face in obj.data.polygons:
                        for loop_index in face.loop_indices:
                            vertex_index = obj.data.loops[loop_index].vertex_index
                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                            # Ajuster les coordonnées des sommets UV
                            new_uv = (
                                (old_uv.x * 0.001) + 0.85,
                                (old_uv.y * 0.001) + 0.53,
                            )  # Modifier l'échelle et la position
                            obj.data.uv_layers[new_uv_map.name].data[
                                loop_index
                            ].uv = new_uv
                    print(
                        "Les coordonnées UV des sommets ont été ajustées avec succès."
                    )

                    # StadiumAirshipO
                elif selected_option == "SAOMap":
                    old_uv_map = obj.data.uv_layers.active
                    for face in obj.data.polygons:
                        for loop_index in face.loop_indices:
                            vertex_index = obj.data.loops[loop_index].vertex_index
                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                            # Ajuster les coordonnées des sommets UV
                            new_uv = (
                                (old_uv.x * 0.001) + 0.03,
                                (old_uv.y * 0.001) + 0.96,
                            )  # Modifier l'échelle et la position
                            obj.data.uv_layers[new_uv_map.name].data[
                                loop_index
                            ].uv = new_uv
                    print(
                        "Les coordonnées UV des sommets ont été ajustées avec succès."
                    )

            else:
                print("L'objet a déjà un deuxième UV Map.")
        else:
            print("Aucun objet actif.")

        return {"FINISHED"}


class OBJECT_OT_AddUVOperator2(bpy.types.Operator):
    bl_idname = "object.add_uv_operator_2"
    bl_label = "Add Light"

    def execute(self, context):
        # Votre code pour le deuxième UV ici
        if bpy.context.active_object:
            obj = bpy.context.active_object
            if len(obj.data.uv_layers) < 2:
                # Obtenez la valeur de l'option sélectionnée
                selected_option = bpy.context.scene.uv_option_2

                # Créez le nouveau UV Map en fonction de l'option sélectionnée
                new_uv_map = obj.data.uv_layers.new(name=f"{selected_option}")
                print(
                    f"UV Map '{new_uv_map.name}' créé avec succès dans les données de l'objet."
                )

                # Modifier les coordonnées UV en fonction de l'option sélectionnée

                # RedLight
                if selected_option == "RedLight":
                    old_uv_map = obj.data.uv_layers.active
                    for face in obj.data.polygons:
                        for loop_index in face.loop_indices:
                            vertex_index = obj.data.loops[loop_index].vertex_index
                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                            # Ajuster les coordonnées des sommets UV
                            new_uv = (
                                (old_uv.x * 0.001) + 0.7,
                                (old_uv.y * 0.001) + 0.14,
                            )  # Modifier l'échelle et la position
                            obj.data.uv_layers[new_uv_map.name].data[
                                loop_index
                            ].uv = new_uv
                    print(
                        "Les coordonnées UV des sommets ont été ajustées avec succès."
                    )

                # GreenLight
                elif selected_option == "GreenLight":
                    old_uv_map = obj.data.uv_layers.active
                    for face in obj.data.polygons:
                        for loop_index in face.loop_indices:
                            vertex_index = obj.data.loops[loop_index].vertex_index
                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                            # Ajuster les coordonnées des sommets UV
                            new_uv = (
                                (old_uv.x * 0.001) + 0.28,
                                (old_uv.y * 0.001) + 0.84,
                            )  # Modifier l'échelle et la position
                            obj.data.uv_layers[new_uv_map.name].data[
                                loop_index
                            ].uv = new_uv
                    print(
                        "Les coordonnées UV des sommets ont été ajustées avec succès."
                    )

                # OrangeLight
                elif selected_option == "OrangeLight":
                    old_uv_map = obj.data.uv_layers.active
                    for face in obj.data.polygons:
                        for loop_index in face.loop_indices:
                            vertex_index = obj.data.loops[loop_index].vertex_index
                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                            # Ajuster les coordonnées des sommets UV
                            new_uv = (
                                (old_uv.x * 0.001) + 0.414,
                                (old_uv.y * 0.001) + 0.514,
                            )  # Modifier l'échelle et la position
                            obj.data.uv_layers[new_uv_map.name].data[
                                loop_index
                            ].uv = new_uv
                    print(
                        "Les coordonnées UV des sommets ont été ajustées avec succès."
                    )
            else:
                print("L'objet a déjà un deuxième UV Map.")
        else:
            print("Aucun objet actif.")

        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_AddUVOperator.bl_idname)
    self.layout.operator(OBJECT_OT_AddUVOperator2.bl_idname)


def register():
    bpy.utils.register_class(OBJECT_PT_MyPanel)
    bpy.utils.register_class(OBJECT_OT_AddUVOperator)
    bpy.utils.register_class(OBJECT_OT_AddUVOperator2)
    bpy.utils.register_class(OBJECT_OT_MyOperatorSeparate)
    bpy.utils.register_class(OBJECT_OT_MergeOperator)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)

    # Ajouter une propriété EnumProperty pour la liste déroulante
    bpy.types.Scene.uv_option = bpy.props.EnumProperty(
        items=[
            ("SROMap", "StadiumRoadO", "StadiumRoadO.dds"),
            ("SRO2Map", "StadiumRoadO2", "StadiumRoadO2.dds"),
            ("SWOmap", "StadiumWarpO", "StadiumWarpO.dds"),
            ("SWO2Map", "StadiumWarpO2", "StadiumWarpO2.dds"),
            ("SGOMap", "StadiumGrassO", "StadiumGrassO.dds"),
            ("SFOMap", "StadiumFabricO", "StadiumFabricO.dds"),
            ("SCOMap", "StadiumControlO", "StadiumControlO.dds"),
            ("SAOMap", "StadiumAirshipO", "StadiumAirshipO.dds"),
        ],
        default="SROMap",  # Option par défaut
        description="Information",
    )

    # Ajouter une deuxième propriété EnumProperty pour le deuxième menu déroulant
    bpy.types.Scene.uv_option_2 = bpy.props.EnumProperty(
        items=[
            ("RedLight", "RedLight", "StadiumStartSignGlow.dds"),
            ("GreenLight", "GreenLight", "StadiumStartSignGlow.dds"),
            ("OrangeLight", "OrangeLight", "StadiumStartSignGlow.dds"),
        ],
        default="RedLight",  # Option par défaut
        description="Information",
    )

    bpy.types.Scene.manual_auto_menu = bpy.props.EnumProperty(
        items=[
            ("Manual", "Manual", ""),
            ("Auto", "Auto", ""),
        ],
        default="Manual",
    )


def unregister():
    bpy.utils.unregister_class(OBJECT_PT_MyPanel)
    bpy.utils.unregister_class(OBJECT_OT_AddUVOperator)
    bpy.utils.unregister_class(OBJECT_OT_AddUVOperator2)
    bpy.utils.unregister_class(OBJECT_OT_MyOperatorSeparate)
    bpy.utils.unregister_class(OBJECT_OT_MergeOperator)
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)


    # Supprimer la propriété EnumProperty lors de la désinscription
    del bpy.types.Scene.uv_option
    del bpy.types.Scene.uv_option_2
    del bpy.types.Scene.manual_auto_menu


if __name__ == "__main__":
    register()
