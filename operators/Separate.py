import bpy

class OBJECT_OT_MyOperatorSeparate(bpy.types.Operator):
    bl_idname = "object.my_operator_separate_2"
    bl_label = "Separate + Modifiers"

    def execute(self, context):
        if bpy.context.selected_objects:
            objet_selectionne = bpy.context.selected_objects[0]
            if objet_selectionne.type == "MESH":
                bpy.context.view_layer.objects.active = objet_selectionne

                # Ajoute le modificateur "Edge Split" à l'objet de base
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

                # Ajouter des UV supplémentaires en fonction des matériaux
                for obj in nouveaux_objets:
                    if obj.data.materials:
                        for slot in obj.material_slots:
                            material_name = slot.material.name
                            if material_name in [
                                "StadiumFabricPool", "StadiumInflatable2Occ", "StadiumPlatform",
                                "StadiumPlatformAuventAlpha", "StadiumPlatformFabric", "StadiumPlatformFabricUnderWater",
                                "StadiumPlatformPillar", "StadiumPlatformPub8x1B", "StadiumPlatformRaceSigns",
                                "StadiumPlatformRoadBorder", "StadiumPlatformRoadDetails", "StadiumPlatformSoundSystem",
                                "StadiumPlatformSpots", "StadiumPlatformStands2", "StadiumPlatformStructureGeneric",
                                "StadiumSculpt", "StadiumSculpt2", "StadiumSculptAuvent2", "StadiumSculptGrassOcc", "StadiumSculptStructureAlpha"
                            ]:
                                if "SRO2Map" not in obj.data.uv_layers:
                                    uv_layer = obj.data.uv_layers.new(name="SRO2Map")
                                    # Initialise les coordonnées UV (optionnel, ici nous les mettons à (0, 0))
                                    for loop in obj.data.loops:
                                        uv_layer.data[loop.index].uv = (0.0, 0.0)
                                    # Modifier les coordonnées UV en fonction de l'option sélectionnée
                                    for face in obj.data.polygons:
                                        for loop_index in face.loop_indices:
                                            vertex_index = obj.data.loops[loop_index].vertex_index
                                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                                            # Ajuster les coordonnées des sommets UV
                                            new_uv = (
                                                (old_uv.x * 0.001) + 0.3,
                                                (old_uv.y * 0.001) + 0.8,
                                            )  # Modifier l'échelle et la position
                                            obj.data.uv_layers["SRO2Map"].data[loop_index].uv = new_uv
                            #StadiumRoadO
                            elif material_name in [
                                "StadiumRoadBorder", "StadiumPillar", "StadiumPlatformFloor",
                                "StadiumRacePub8x1A", "StadiumRacePub8x1B", "StadiumRacePub8x1C",
                                "StadiumRacePub8x1D", "StadiumRaceSignRubber", "StadiumRoad",
                                "StadiumRoadBorder", "StadiumRoadBorderMetal", "StadiumRoadBorderRubber",
                                "StadiumRoadDetails", "StadiumRoadDirtTurbo", "StadiumRoadFreeWheeling",
                                "StadiumRoadGrid", "StadiumRoadRace", "StadiumRoadTurbo",
                                "StadiumRoadTurboRoulette", "StadiumStartLogo", "StadiumStartSign",
                                "StadiumTurboAlpha", "StadiumTurboSpots", "StadiumTurboStands2"
                            ]:
                                if "SROMap" not in obj.data.uv_layers:
                                    uv_layer = obj.data.uv_layers.new(name="SROMap")
                                    # Initialise les coordonnées UV (optionnel, ici nous les mettons à (0, 0))
                                    for loop in obj.data.loops:
                                        uv_layer.data[loop.index].uv = (0.0, 0.0)
                                    # Modifier les coordonnées UV en fonction de l'option sélectionnée
                                    for face in obj.data.polygons:
                                        for loop_index in face.loop_indices:
                                            vertex_index = obj.data.loops[loop_index].vertex_index
                                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                                            # Ajuster les coordonnées des sommets UV
                                            new_uv = (
                                                (old_uv.x * 0.001) + 0.3,
                                                (old_uv.y * 0.001) + 0.8,
                                            )  # Modifier l'échelle et la position
                                            obj.data.uv_layers["SROMap"].data[loop_index].uv = new_uv


                            #StadiumGrassO
                            elif material_name in [
                                "StadiumDirt", "StadiumDirtAuvent2", "StadiumDirtBorder",
                                "StadiumDirtFabric", "StadiumDirtGrid", "StadiumDirtLogos",
                                "StadiumDirtPub2x1", "StadiumDirtNvidiaWorldCup", "StadiumDirtRacePub8x1A",
                                "StadiumDirtRaceSignsRubber", "StadiumDirtRoad", "StadiumDirtRoadBorder",
                                "StadiumDirtRoadDetails", "StadiumDirtStructureGeneric", "StadiumDirtToRoad",
                                "StadiumFabricFloor", "StadiumGrassOcc", "StadiumGrassOcc9m",
                                "StadiumGrassOccNoFence", "StadiumRoadDirtToRoad", "StadiumRoadDirtToRoadFlat", "StadiumRoadToDirt"
                            ]:
                                if "SGOMap" not in obj.data.uv_layers:
                                    uv_layer = obj.data.uv_layers.new(name="SGOMap")
                                    # Initialise les coordonnées UV (optionnel, ici nous les mettons à (0, 0))
                                    for loop in obj.data.loops:
                                        uv_layer.data[loop.index].uv = (0.0, 0.0)
                                    # Modifier les coordonnées UV en fonction de l'option sélectionnée
                                    for face in obj.data.polygons:
                                        for loop_index in face.loop_indices:
                                            vertex_index = obj.data.loops[loop_index].vertex_index
                                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                                            # Ajuster les coordonnées des sommets UV
                                            new_uv = (
                                                (old_uv.x * 0.001) + 0.21,
                                                (old_uv.y * 0.001) + 0.6,
                                            )  # Modifier l'échelle et la position
                                            obj.data.uv_layers["SGOMap"].data[loop_index].uv = new_uv


                            #StadiumWarpO2
                            elif material_name in [
                                "StadiumWarpAuventAlphaBis", "StadiumWarpGrass", "StadiumWarpGrassPreLightGen",
                                "StadiumWarpParvis", "StadiumWarpRoute"
                            ]:
                                if "SWO2Map" not in obj.data.uv_layers:
                                    uv_layer = obj.data.uv_layers.new(name="SWO2Map")
                                    # Initialise les coordonnées UV (optionnel, ici nous les mettons à (0, 0))
                                    for loop in obj.data.loops:
                                        uv_layer.data[loop.index].uv = (0.0, 0.0)
                                    # Modifier les coordonnées UV en fonction de l'option sélectionnée
                                    for face in obj.data.polygons:
                                        for loop_index in face.loop_indices:
                                            vertex_index = obj.data.loops[loop_index].vertex_index
                                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                                            # Ajuster les coordonnées des sommets UV
                                            new_uv = (
                                                (old_uv.x * 0.001) + 0.01,
                                                (old_uv.y * 0.001) + 0.98,
                                            )  # Modifier l'échelle et la position
                                            obj.data.uv_layers["SWO2Map"].data[loop_index].uv = new_uv




                            #StadiumControlO
                            elif material_name in [
                                "StadiumControlAuvent", "StadiumControlAuvent2", "StadiumControlAuventAlpha",
                                "StadiumControlGlass", "StadiumControlInterior", "StadiumControlLogos",
                                "StadiumControlSpots", "StadiumControlStands", "StadiumControlStands2",
                                "StadiumControlStands3", "StadiumInflatable", "StadiumInflatable2", "StadiumPubNvidiaWorldcup"
                            ]:
                                if "SCOMap" not in obj.data.uv_layers:
                                    uv_layer = obj.data.uv_layers.new(name="SCOMap")
                                    # Initialise les coordonnées UV (optionnel, ici nous les mettons à (0, 0))
                                    for loop in obj.data.loops:
                                        uv_layer.data[loop.index].uv = (0.0, 0.0)
                                    # Modifier les coordonnées UV en fonction de l'option sélectionnée
                                    for face in obj.data.polygons:
                                        for loop_index in face.loop_indices:
                                            vertex_index = obj.data.loops[loop_index].vertex_index
                                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                                            # Ajuster les coordonnées des sommets UV
                                            new_uv = (
                                                (old_uv.x * 0.001) + 0.01,
                                                (old_uv.y * 0.001) + 0.98,
                                            )  # Modifier l'échelle et la position
                                            obj.data.uv_layers["SCOMap"].data[loop_index].uv = new_uv
                                            
                                            
                            #StadiumLoopO
                            elif material_name in [
                                "StadiumLoopPillar", "StadiumLoopRoadBorderMetal", "StadiumLoopRoadBorderRubber",
                                "StadiumLoopRoadDetails", "StadiumLoopRoadGrid"
                            ]:
                                if "SLOMap" not in obj.data.uv_layers:
                                    uv_layer = obj.data.uv_layers.new(name="SLOMap")
                                    # Initialise les coordonnées UV (optionnel, ici nous les mettons à (0, 0))
                                    for loop in obj.data.loops:
                                        uv_layer.data[loop.index].uv = (0.0, 0.0)
                                    # Modifier les coordonnées UV en fonction de l'option sélectionnée
                                    for face in obj.data.polygons:
                                        for loop_index in face.loop_indices:
                                            vertex_index = obj.data.loops[loop_index].vertex_index
                                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                                            # Ajuster les coordonnées des sommets UV
                                            new_uv = (
                                                (old_uv.x * 0.001) + 0.85,
                                                (old_uv.y * 0.001) + 0.25,
                                            )  # Modifier l'échelle et la position
                                            obj.data.uv_layers["SLOMap"].data[loop_index].uv = new_uv  


                            #StadiumInflatableCactusO
                            elif material_name in [
                                "StadiumInflatableCactus", "StadiumInflatableCastle", "StadiumInflatableSnowTree"
                            ]:
                                if "SICOMap" not in obj.data.uv_layers:
                                    uv_layer = obj.data.uv_layers.new(name="SICOMap")
                                    # Initialise les coordonnées UV (optionnel, ici nous les mettons à (0, 0))
                                    for loop in obj.data.loops:
                                        uv_layer.data[loop.index].uv = (0.0, 0.0)
                                    # Modifier les coordonnées UV en fonction de l'option sélectionnée
                                    for face in obj.data.polygons:
                                        for loop_index in face.loop_indices:
                                            vertex_index = obj.data.loops[loop_index].vertex_index
                                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                                            # Ajuster les coordonnées des sommets UV
                                            new_uv = (
                                                (old_uv.x * 0.001) + 0.05,
                                                (old_uv.y * 0.001) + 0.05,
                                            )  # Modifier l'échelle et la position
                                            obj.data.uv_layers["SICOMap"].data[loop_index].uv = new_uv  



                            #StadiumAirshipO
                            elif material_name in [
                                "StadiumAirship"
                            ]:
                                if "SAOMap" not in obj.data.uv_layers:
                                    uv_layer = obj.data.uv_layers.new(name="SAOMap")
                                    # Initialise les coordonnées UV (optionnel, ici nous les mettons à (0, 0))
                                    for loop in obj.data.loops:
                                        uv_layer.data[loop.index].uv = (0.0, 0.0)
                                    # Modifier les coordonnées UV en fonction de l'option sélectionnée
                                    for face in obj.data.polygons:
                                        for loop_index in face.loop_indices:
                                            vertex_index = obj.data.loops[loop_index].vertex_index
                                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                                            # Ajuster les coordonnées des sommets UV
                                            new_uv = (
                                                (old_uv.x * 0.001) + 0.03,
                                                (old_uv.y * 0.001) + 0.95,
                                            )  # Modifier l'échelle et la position
                                            obj.data.uv_layers["SAOMap"].data[loop_index].uv = new_uv 


                            #StadiumWarpGlassO
                            elif material_name in [
                                "StadiumWarpGlass"
                            ]:
                                if "SWGOMap" not in obj.data.uv_layers:
                                    uv_layer = obj.data.uv_layers.new(name="SWGOMap")
                                    # Initialise les coordonnées UV (optionnel, ici nous les mettons à (0, 0))
                                    for loop in obj.data.loops:
                                        uv_layer.data[loop.index].uv = (0.0, 0.0)
                                    # Modifier les coordonnées UV en fonction de l'option sélectionnée
                                    for face in obj.data.polygons:
                                        for loop_index in face.loop_indices:
                                            vertex_index = obj.data.loops[loop_index].vertex_index
                                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                                            # Ajuster les coordonnées des sommets UV
                                            new_uv = (
                                                (old_uv.x * 0.001) + 0.05,
                                                (old_uv.y * 0.001) + 0.05,
                                            )  # Modifier l'échelle et la position
                                            obj.data.uv_layers["SWGOMap"].data[loop_index].uv = new_uv
                                            
                                            
                                            
                            #StadiumInflatablePalmTreeO
                            elif material_name in [
                                "StadiumInflatablePalmTree"
                            ]:
                                if "SIPTOMap" not in obj.data.uv_layers:
                                    uv_layer = obj.data.uv_layers.new(name="SIPTOMap")
                                    # Initialise les coordonnées UV (optionnel, ici nous les mettons à (0, 0))
                                    for loop in obj.data.loops:
                                        uv_layer.data[loop.index].uv = (0.0, 0.0)
                                    # Modifier les coordonnées UV en fonction de l'option sélectionnée
                                    for face in obj.data.polygons:
                                        for loop_index in face.loop_indices:
                                            vertex_index = obj.data.loops[loop_index].vertex_index
                                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                                            # Ajuster les coordonnées des sommets UV
                                            new_uv = (
                                                (old_uv.x * 0.001) + 0.7,
                                                (old_uv.y * 0.001) + 0.5,
                                            )  # Modifier l'échelle et la position
                                            obj.data.uv_layers["SIPTOMap"].data[loop_index].uv = new_uv                

                                            



                            #StadiumFabricO
                            elif material_name in [
                                "StadiumCircuit", "StadiumCircuitLogo", "StadiumFabric",
                                "StadiumFabricAuvent", "StadiumFabricAuvent2", "StadiumFabricAuventAlpha",
                                "StadiumFabricBorderRubber", "StadiumFabricInterior", "StadiumFabricPlatformFloor",
                                "StadiumFabricRoadDetails", "StadiumFabricSpots", "StadiumFabricStands",
                                "StadiumFabricStands2", "StadiumFabricStructure", "StadiumRoadCircuitBorder",
                                "StadiumStructureAlpha", "StadiumStructureGeneric"
                            ]:
                                if "SFOMap" not in obj.data.uv_layers:
                                    uv_layer = obj.data.uv_layers.new(name="SFOMap")
                                    # Initialise les coordonnées UV (optionnel, ici nous les mettons à (0, 0))
                                    for loop in obj.data.loops:
                                        uv_layer.data[loop.index].uv = (0.0, 0.0)
                                    # Modifier les coordonnées UV en fonction de l'option sélectionnée
                                    for face in obj.data.polygons:
                                        for loop_index in face.loop_indices:
                                            vertex_index = obj.data.loops[loop_index].vertex_index
                                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                                            # Ajuster les coordonnées des sommets UV
                                            new_uv = (
                                                (old_uv.x * 0.001) + 0.52,
                                                (old_uv.y * 0.001) + 0.82,
                                            )  # Modifier l'échelle et la position
                                            obj.data.uv_layers["SFOMap"].data[loop_index].uv = new_uv

                            #StadiumWarpO
                            elif material_name in [
                                "StadiumWarpAuvent", "StadiumWarpAuvent2", "StadiumWarpAuventAlpha",
                                "StadiumWarpLogos", "StadiumWarpParking", "StadiumWarpPub8x1E",
                                "StadiumWarpPub8x1F", "StadiumWarpPub8x1G", "StadiumWarpPub8x1H",
                                "StadiumWarpPub8x1I", "StadiumWarpSpots", "StadiumWarpStands", "StadiumWarpStands2"
                            ]:
                                if "SWOMap" not in obj.data.uv_layers:
                                    uv_layer = obj.data.uv_layers.new(name="SWOMap")
                                    # Initialise les coordonnées UV (optionnel, ici nous les mettons à (0, 0))
                                    for loop in obj.data.loops:
                                        uv_layer.data[loop.index].uv = (0.0, 0.0)
                                    # Modifier les coordonnées UV en fonction de l'option sélectionnée
                                    for face in obj.data.polygons:
                                        for loop_index in face.loop_indices:
                                            vertex_index = obj.data.loops[loop_index].vertex_index
                                            old_uv = obj.data.uv_layers.active.data[loop_index].uv
                                            # Ajuster les coordonnées des sommets UV
                                            new_uv = (
                                                (old_uv.x * 0.001) + 0.33,
                                                (old_uv.y * 0.001) + 0.09,
                                            )  # Modifier l'échelle et la position
                                            obj.data.uv_layers["SWOMap"].data[loop_index].uv = new_uv

                            # Supprimer le UVMap pour les matériaux "StadiumGrass1" etc...
                            elif material_name in [
                                "StadiumGrass1", "StadiumFabricFloorNoOcc", "StadiumFan", "StadiumGrass", "StadiumGrass9m",
                                "StadiumGrassFence", "StadiumStartSignGlow", "StadiumWarpSpotsGlow", "StadiumWarpSpotsGlowBack", "StadiumWater"
                            ]:
                                if "BaseMaterial" in obj.data.uv_layers:
                                    obj.data.uv_layers.remove(obj.data.uv_layers["BaseMaterial"])


                self.report({'INFO'}, "Tous les objets ont été créés avec succès et parentés de manière hiérarchique à l'objet initial.")
            else:
                self.report({'WARNING'}, "L'objet sélectionné n'est pas un objet de type MESH.")
        else:
            self.report({'WARNING'}, "Aucun objet sélectionné.")

        return {"FINISHED"}

def register_separate():
    bpy.utils.register_class(OBJECT_OT_MyOperatorSeparate)

def unregister_separate():
    bpy.utils.unregister_class(OBJECT_OT_MyOperatorSeparate)
