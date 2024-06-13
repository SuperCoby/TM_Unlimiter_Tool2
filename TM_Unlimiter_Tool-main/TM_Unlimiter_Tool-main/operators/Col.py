import bpy

# Créer une classe d'opérateur pour dupliquer l'objet et fusionner les matériaux
class OBJECT_OT_duplicate_and_merge(bpy.types.Operator):
    bl_idname = "object.duplicate_and_merge"
    bl_label = "Duplicate and Merge Materials"
    bl_description = "Duplicate the active object and merge its materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not is_collision_material_set():
            print("La propriété collision_material n'est pas définie. La classe est désactivée.")
            return {'CANCELLED'}
        
        duplicate_object()
        return {'FINISHED'}

def is_collision_material_set():
    # Vérifier si la propriété collision_material est définie dans le matériau actif
    if bpy.context.object.active_material is not None and hasattr(bpy.context.object.active_material, 'unlimiter_material_collision'):
        return hasattr(bpy.context.object.active_material.unlimiter_material_collision, 'collision_material')
    return False

def duplicate_object():
    # Sélectionner l'objet actif
    selected_obj = bpy.context.active_object

    # Vérifier si l'objet sélectionné est valide
    if selected_obj is not None:
        # Dupliquer l'objet
        new_obj = selected_obj.copy()
        new_obj.data = selected_obj.data.copy()
        new_obj.name = f"{selected_obj.name}_Col"

        # Ajouter l'objet dupliqué à la scène
        bpy.context.collection.objects.link(new_obj)

        # Sélectionner uniquement l'objet dupliqué
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        bpy.context.view_layer.objects.active = new_obj

        # Créer et assigner les matériaux
        # Concrete
        concrete_material = bpy.data.materials.new(name="Concrete")
        concrete_material.diffuse_color = (0, 0, 0, 1)
        concrete_material.roughness = 1.0
        new_obj.data.materials.append(concrete_material)

        concrete_materials_to_merge = ["StadiumWarpAuvent2", "StadiumDirtPub2x1", "StadiumPlatform", "StadiumCircuit", "StadiumRoadBorder", "StadiumAirship",
        "StadiumCircuitLogo", "StadiumControlInterior", "StadiumControlAuvent2", "StadiumControlAuvent", "StadiumDirtGrid", "StadiumFabric", "StadiumFabricFloor", "StadiumFabricPool",
        "StadiumFabricStructure", "StadiumInflatable2", "StadiumInflatableCactus", "StadiumInflatableCastle", "StadiumInflatable",
        "StadiumInflatablePalmTree", "StadiumInflatableSnowTree", "StadiumStartLogo", "StadiumPillar", "StadiumPlatformFloor", "StadiumPubNvidiaWorldcup",
        "StadiumRaceSignsRubber", "StadiumRoadCircuitBorder", "StadiumRoad", "StadiumRoadDetails", "StadiumRoadGrid", "StadiumRoadRace",
        "StadiumRoadToDirt", "StadiumSculpt2", "StadiumSculpt", "StadiumStructureAlpha", "StadiumSoundSystem", "StadiumStartLogoD", "StadiumStructureAlphaD",
        "StadiumStructureGeneric", "StadiumWarpAuvent2S", "StadiumWarpAuventAlpha", "StadiumWarpAuvent", "StadiumWarpLogos", "StadiumWarpParking",
        "StadiumWarpParvis", "StadiumWarpRoute", "StadiumWarpSpots", "StadiumWarpStands2", "StadiumWarpStands"]

        # Grass
        grass_material = bpy.data.materials.new(name="Grass")
        grass_material.diffuse_color = (0, 1, 0, 1)
        grass_material.roughness = 1.0
        new_obj.data.materials.append(grass_material)

        grass_materials_to_merge = ["StadiumGrass", "StadiumGrass1", "StadiumGrass2"]
        
        # Ice
        ice_material = bpy.data.materials.new(name="Ice")
        ice_material.diffuse_color = (0, 0, 1, 1)
        ice_material.roughness = 1.0
        new_obj.data.materials.append(ice_material)

        ice_materials_to_merge = ["StadiumControlGlass", "StadiumWarpGlass"]

        # Dirt
        dirt_material = bpy.data.materials.new(name="Dirt")
        dirt_material.diffuse_color = (0.3, 0.15, 0, 1)
        dirt_material.roughness = 1.0
        new_obj.data.materials.append(dirt_material)

        dirt_materials_to_merge = ["StadiumDirt", "StadiumDirt1", "StadiumDirt2", "StadiumDirtRoad", "StadiumDirtRoadBorder", "StadiumRoadDirtToRoad"]

        # NotCollide
        not_collide_material = bpy.data.materials.new(name="NotCollide")
        not_collide_material.diffuse_color = (1, 1, 1, 1)
        not_collide_material.roughness = 1.0
        new_obj.data.materials.append(not_collide_material)

        not_collide_materials_to_merge = ["StadiumStartSignGlow", "StadiumWarpSpotsGlow", "StadiumFan", "StadiumStartSign", "StadiumGrassFence", "StadiumGrassStripe"]

        # Turbo
        turbo_material = bpy.data.materials.new(name="Turbo")
        turbo_material.diffuse_color = (0.7, 0.5, 0, 1)
        turbo_material.roughness = 1.0
        new_obj.data.materials.append(turbo_material)

        turbo_materials_to_merge = ["StadiumRoadTurbo", "StadiumRoadDirtTurbo"]

        # FreeWheeling
        fw_material = bpy.data.materials.new(name="FreeWheeling")
        fw_material.diffuse_color = (1, 0, 1, 1)
        fw_material.roughness = 1.0
        new_obj.data.materials.append(fw_material)

        fw_materials_to_merge = ["StadiumRoadFreeWheeling"]

        # TurboRoulette
        turbo_roulette_material = bpy.data.materials.new(name="TurboR")
        turbo_roulette_material.diffuse_color = (1, 0, 0, 1)
        turbo_roulette_material.roughness = 1.0
        new_obj.data.materials.append(turbo_roulette_material)

        turbo_roulette_materials_to_merge = ["StadiumRoadTurboRoulette"]

        # Assign materials to faces based on their original material
        for poly in new_obj.data.polygons:
            original_material_name = new_obj.data.materials[poly.material_index].name
            if original_material_name in concrete_materials_to_merge:
                poly.material_index = new_obj.data.materials.find(concrete_material.name)
            elif original_material_name in grass_materials_to_merge:
                poly.material_index = new_obj.data.materials.find(grass_material.name)
            elif original_material_name in dirt_materials_to_merge:
                poly.material_index = new_obj.data.materials.find(dirt_material.name)
            elif original_material_name in not_collide_materials_to_merge:
                poly.material_index = new_obj.data.materials.find(not_collide_material.name)
            elif original_material_name in turbo_materials_to_merge:
                poly.material_index = new_obj.data.materials.find(turbo_material.name)
            elif original_material_name in fw_materials_to_merge:
                poly.material_index = new_obj.data.materials.find(fw_material.name)
            elif original_material_name in turbo_roulette_materials_to_merge:
                poly.material_index = new_obj.data.materials.find(turbo_roulette_material.name)
            elif original_material_name in ice_materials_to_merge:
                poly.material_index = new_obj.data.materials.find(ice_material.name)                

        # Supprimer les emplacements de matériaux inutilisés
        bpy.ops.object.material_slot_remove_unused()

        # Configurer les paramètres spécifiques des matériaux
        for mat in new_obj.data.materials:
            if hasattr(mat, 'unlimiter_material_collision'):  # Vérifiez que l'attribut existe
                mat.unlimiter_material_collision.is_collidable = True
                if mat.name == "Concrete":
                    mat.unlimiter_material_collision.is_collidable = True
                elif mat.name == "Grass":
                    mat.unlimiter_material_collision.collision_material = '2'
                elif mat.name == "Dirt":
                    mat.unlimiter_material_collision.collision_material = '6'
                elif mat.name == "NotCollide":
                    mat.unlimiter_material_collision.is_collidable = False
                elif mat.name == "Turbo":
                    mat.unlimiter_material_collision.collision_material = '7'
                elif mat.name == "FreeWheeling":
                    mat.unlimiter_material_collision.collision_material = '29'
                elif mat.name == "TurboR":
                    mat.unlimiter_material_collision.collision_material = '30'
                elif mat.name == "Ice":
                    mat.unlimiter_material_collision.collision_material = '3'                    

        # Configurer les paramètres spécifiques de l'objet
        new_obj.unlimiter_object_settings.can_export_geometry = False
        new_obj.unlimiter_object_settings.can_export_collision = True

        print("Objet dupliqué avec succès et matériaux fusionnés.")
    else:
        print("Aucun objet sélectionné ou objet actif invalide.")

# Enregistrer les classes
def register_col():
    bpy.utils.register_class(OBJECT_OT_duplicate_and_merge)

def unregister_col():
    bpy.utils.unregister_class(OBJECT_OT_duplicate_and_merge)
