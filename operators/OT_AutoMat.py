import bpy
import re

# Fonction pour ajuster les propriétés de l'objet en fonction du nom du matériau
def adjust_object_settings(obj, material_name):
    obj.unlimiter_object_settings.texture_props.texture_type = 'Game'
    obj.unlimiter_object_settings.texture_props.texture_game.game_material = (
        f"{material_name}.Material.Gbx"
    )


# Liste des matériaux après StadiumRoadBorder
material_list = [
    "StadiumControlAuvent",
    "StadiumControlAuvent2",
    "StadiumControlAuventAlpha",
    "StadiumControlGlass",
    "StadiumControlInterior",
    "StadiumControlLogos",
    "StadiumControlSpots",
    "StadiumControlStands",
    "StadiumControlStands2",
    "StadiumControlStands3",
    "StadiumInflatable",
    "StadiumInflatable2",
    "StadiumPubNvidiaWorldcup",
    "StadiumFabricPool",
    "StadiumInflatable2Occ",
    "StadiumPlatform",
    "StadiumPlatformAuventAlpha",
    "StadiumPlatformFabric",
    "StadiumPlatformFabricUnderWater",
    "StadiumPlatformPillar",
    "StadiumPlatformPub8x1B",
    "StadiumPlatformRaceSigns",
    "StadiumPlatformRoadBorder",
    "StadiumPlatformRoadDetails",
    "StadiumPlatformSoundSystem",
    "StadiumPlatformSpots",
    "StadiumPlatformStands2",
    "StadiumPlatformStructureGeneric",
    "StadiumSculpt",
    "StadiumSculpt2",
    "StadiumSculptAuvent2",
    "StadiumSculptGrassOcc",
    "StadiumSculptStructureAlpha",
    "StadiumPillar",
    "StadiumPlatformFloor",
    "StadiumRacePub8x1A",
    "StadiumRacePub8x1B",
    "StadiumRacePub8x1C",
    "StadiumRacePub8x1D",
    "StadiumRaceSignsRubber",
    "StadiumRoad",
    "StadiumRoadBorder",
    "StadiumRoadBorderMetal",
    "StadiumRoadBorderRubber",
    "StadiumRoadDetails",
    "StadiumRoadDirtTurbo",
    "StadiumRoadFreeWheeling",
    "StadiumRoadGrid",
    "StadiumRoadRace",
    "StadiumRoadTurbo",
    "StadiumRoadTurboRoulette",
    "StadiumStartLogo",
    "StadiumStartSign",
    "StadiumTurboAlpha",
    "StadiumTurboSpots",
    "StadiumTurboStands2",
    "StadiumDirt",
    "StadiumDirtAuvent2",
    "StadiumDirtBorder",
    "StadiumDirtFabric",
    "StadiumDirtGrid",
    "StadiumDirtLogos",
    "StadiumDirtPub2x1",
    "StadiumDirtNvidiaWorldCup",
    "StadiumDirtRacePub8x1A",
    "StadiumDirtRaceSignsRubber",
    "StadiumDirtRoad",
    "StadiumDirtRoadBorder",
    "StadiumDirtRoadDetails",
    "StadiumDirtStructureGeneric",
    "StadiumDirtToRoad",
    "StadiumFabricFloor",
    "StadiumGrassOcc",
    "StadiumGrassOcc9m",
    "StadiumGrassOccNoFence",
    "StadiumRoadDirtToRoad",
    "StadiumRoadDirtToRoadFlat",
    "StadiumRoadToDirt",
    "StadiumCircuit",
    "StadiumCircuitLogo",
    "StadiumFabric",
    "StadiumFabricAuvent",
    "StadiumFabricAuvent2",
    "StadiumFabricAuventAlpha",
    "StadiumFabricBorderRubber",
    "StadiumFabricInterior",
    "StadiumFabricPlatformFloor",
    "StadiumFabricRoadDetails",
    "StadiumFabricSpots",
    "StadiumFabricStands",
    "StadiumFabricStands2",
    "StadiumFabricStructure",
    "StadiumRoadCircuitBorder",
    "StadiumStructureAlpha",
    "StadiumStructureGeneric",
    "StadiumWarpAuvent",
    "StadiumWarpAuvent2",
    "StadiumWarpAuventAlpha",
    "StadiumWarpLogos",
    "StadiumWarpParking",
    "StadiumWarpPub8x1E",
    "StadiumWarpPub8x1F",
    "StadiumWarpPub8x1G",
    "StadiumWarpPub8x1H",
    "StadiumWarpPub8x1I",
    "StadiumWarpSpots",
    "StadiumWarpStands",
    "StadiumWarpStands2",
    "StadiumWarpAuventAlphaBis",
    "StadiumWarpGrass",
    "StadiumWarpGrassPreLightGen",
    "StadiumWarpParvis",
    "StadiumWarpRoute",
    "StadiumLoopPillar",
    "StadiumLoopRoadBorderMetal",
    "StadiumLoopRoadBorderRubber",
    "StadiumLoopRoadDetails",
    "StadiumLoopRoadGrid",
    "StadiumInflatableCactus",
    "StadiumInflatableCastle",
    "StadiumInflatableSnowTree",
    "StadiumAirship",
    "StadiumWarpGlass",
    "StadiumInflatablePalmTree",
    "StadiumCircuitScreen",
    "StadiumControlScreen2x1",
    "StadiumScreen2x1",
    "StadiumScreen8x1A",
    "StadiumScreen8x1B",
    "StadiumScreen8x1C",
    "StadiumScreen8x1D",
    "StadiumScreenArrow2x1",
    "StadiumWarpScreen2x1East",
    "StadiumWarpScreen2x1West",
    "StadiumWarpScreen8x1A",
    "StadiumWarpScreen8x1B",
    "StadiumWarpScreen8x1C",
    "StadiumWarpScreen8x1D",
    "StadiumFabricFloorNoOcc",
    "StadiumFan",
    "StadiumGrass",
    "StadiumGrass9m",
    "StadiumGrassFence",
    "StadiumStartSignGlow",
    "StadiumWarpFlag(A-X)",
    "StadiumWarpSpotsGlow",
    "StadiumWarpSpotsGlowBack",
    "StadiumWater",
]


# Matériau de collision de chaque material : nom de la surface dans la liste de collisions de
# tmunlimiter (material_collision/default_collision_materials.py, "#17: Asphalt" -> "Asphalt").
# Bump/Bump2/Turbo "_Deprecated" et RubberBand n'existent pas dans TMNF : surface la plus proche.
collision_list = {
    "StadiumPlatform": "Asphalt",
    "StadiumPillar": "Asphalt",
    "StadiumControlInterior": "Asphalt",
    "StadiumFabricStructure": "Asphalt",
    "StadiumPlatformFloor": "Asphalt",
    "StadiumRoad": "Asphalt",
    "StadiumRoadBorder": "Asphalt",
    "StadiumRoadDirtToRoad": "Asphalt",
    "StadiumRoadRace": "Asphalt",
    "StadiumRoadToDirt": "Asphalt",
    "StadiumFabric": "Asphalt",
    "StadiumBumper": "Bumper",
    "StadiumBumper2": "Bumper",
    "StadiumFabricFloor": "Concrete",
    "StadiumInflatable2": "Concrete",
    "StadiumControlSpots": "Concrete",
    "StadiumControlSpotsON": "Concrete",
    "StadiumControlStands": "Concrete",
    "StadiumControlStands2": "Concrete",
    "StadiumControlStands3": "Concrete",
    "StadiumInflatable": "Concrete",
    "StadiumDirt": "Dirt",
    "StadiumDirtBorder": "Dirt",
    "StadiumRoadDirtToRoadFlat": "Dirt",
    "StadiumDirtRoad": "Dirt",
    "StadiumDirtToRoad": "Dirt",
    "StadiumGrass": "Grass",
    "StadiumGrass9m": "Grass",
    "StadiumGrassOccNoFence": "Grass",
    "StadiumWarpGrassPreLightGen": "Grass",
    "StadiumControlGlass": "Ice",
    "StadiumCircuit": "Metal",
    "StadiumRoadGrid2": "Metal",
    "StadiumFence": "Metal",
    "StadiumStructureGeneric": "Metal",
    "StadiumCircuitLogo": "Metal",
    "StadiumControlAuvent": "Metal",
    "StadiumControlAuvent2": "Metal",
    "StadiumControlAuventAlpha": "Metal",
    "StadiumControlLogos": "Metal",
    "StadiumPlatformSoundSystem": "Metal",
    "StadiumPubNvidiaWorldcup": "Metal",
    "StadiumRoadBorderMetal": "Metal",
    "StadiumRoadDetails": "Metal",
    "StadiumRoadGrid": "Metal",
    "StadiumSculpt": "Metal",
    "StadiumSculpt2": "Metal",
    "StadiumStartLogo": "Metal",
    "StadiumStartSign": "Metal",
    "StadiumStructureAlpha": "Metal",
    "StadiumStructureGeneric2": "Metal",
    "StadiumTurboDetails": "Metal",
    "StadiumDirtRacePub8x1A": "Metal",
    "StadiumCircuitNotCollidable": "NotCollidable",
    "StadiumDecoPaint": "ResonantMetal",
    "StadiumRaceArch": "Rubber",
    "StadiumRaceSignsRubber": "Rubber",
    "StadiumRoadBorderRubber": "Rubber",
    "StadiumRoadCircuitBorder": "Rubber",
    "StadiumRoadBorderRubberBand": "Rubber",
    "StadiumDirtPub2x1": "SlidingRubber",
    "StadiumFabricPool": "SlidingRubber",
    "StadiumRoadDirtTurbo": "Turbo",
    "StadiumRoadTurbo": "Turbo",
}


def base_material_name(name):
    """Nom sans le suffixe ajouté par Blender aux doublons, ex. "StadiumGrass.001" -> "StadiumGrass" """
    return re.sub(r"\.\d{3}$", "", name)


def adjust_material_collision(material, material_name):
    surface = collision_list.get(material_name)
    if surface is None or not hasattr(material, "unlimiter_material_collision"):
        return False

    collision = material.unlimiter_material_collision
    # Identifiant tmunlimiter de la surface : ("16", "#17: Asphalt", ...) -> "16"
    items = collision.bl_rna.properties["collision_material"].enum_items
    identifier = next((item.identifier for item in items if item.name.split(": ", 1)[-1] == surface), None)
    if identifier is None:
        return False

    collision.is_collidable = True
    collision.collision_material = identifier
    return True


class TM_OT_AUTOMAT(bpy.types.Operator):
    bl_idname = "object.automat"
    bl_label = "Auto Mat"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        if not are_texture_props_set():
            print("Les propriétés de texture ne sont pas définies. La classe est désactivée.")
            return {'CANCELLED'}

        # Parcourir les objets sélectionnés dans la scène
        selected_objects = bpy.context.selected_objects
        for obj in selected_objects:
            # Inclure l'objet et ses parents dans le traitement
            objects_to_process = {obj}
            parent = obj.parent
            while parent:
                objects_to_process.add(parent)
                parent = parent.parent
            
            # Traiter chaque objet
            for obj in objects_to_process:
                # Vérifier si l'objet a un matériau
                if obj.material_slots and obj.material_slots[0].material:
                    # Récupérer le nom du premier matériau de l'objet (supposant qu'il n'y en a qu'un)
                    material = obj.material_slots[0].material
                    material_name = base_material_name(material.name)
                    print(f"Matériau détecté : {material_name}")
                    # Vérifier si le nom du matériau est dans la liste complète
                    if material_name in material_list:
                        print(f"Matériau {material_name} trouvé dans la liste.")
                        adjust_object_settings(obj, material_name)
                    else:
                        print(f"Matériau {material_name} n'a pas été trouvé dans la liste.")
                    # Collision du matériau (is_collidable + collision_material)
                    if adjust_material_collision(material, material_name):
                        print(f"Collision {collision_list[material_name]} appliquée à {material.name}.")
                        
        try:
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        except RuntimeError:
            pass  # pas de fenêtre (Blender en arrière-plan)
        return {"FINISHED"}

def are_texture_props_set():
    # Vérifier si les propriétés texture_type et texture_game.game_material sont définies dans unlimiter_object_settings.texture_props
    obj = bpy.context.object
    if obj is not None and hasattr(obj, 'unlimiter_object_settings') and hasattr(obj.unlimiter_object_settings, 'texture_props'):
        texture_props = obj.unlimiter_object_settings.texture_props
        return hasattr(texture_props, 'texture_type') and hasattr(texture_props, 'texture_game') and hasattr(texture_props.texture_game, 'game_material')
    return False


classes = (
    TM_OT_AUTOMAT,
)
