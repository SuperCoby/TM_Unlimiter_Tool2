import bpy
import sys

# Accès à l'addon tmunlimiter_blender_plugin (Tomek0055), qui n'est pas livré avec cet addon :
# tout ce qui l'utilise doit vérifier sa présence avant (il peut être absent ou désactivé).

PLUGIN = "tmunlimiter_blender_plugin"


def module(name):
    """Sous-module chargé de tmunlimiter, ex. module("props.block_definitions_panel"), ou None."""
    return sys.modules.get(f"{PLUGIN}.{name}")


def plugin_loaded():
    return hasattr(bpy.types.Scene, "tmunlimiter_block_definitions") and module("props.block_definitions_panel") is not None


def tmunlimiter_enabled():
    """Propriétés d'objet `unlimiter_object_settings` disponibles."""
    return hasattr(bpy.types.Object, "unlimiter_object_settings")


def has_material_collision():
    """Propriétés de matériau `unlimiter_material_collision` disponibles."""
    return hasattr(bpy.types.Material, "unlimiter_material_collision")


GAME_MATERIAL_MODULES = ("stadium", "alpine", "bay", "coast", "island", "rally", "speed")


def game_materials():
    """[(nom sans ".Material.Gbx", [textures utilisées hors occlusion])] de tous les environnements
    de tmunlimiter, ou [] s'il n'est pas chargé."""
    result = []
    for name in GAME_MATERIAL_MODULES:
        mod = module(f"object_texture.game_materials.{name}")
        if mod is None:
            continue
        for material, groups in getattr(mod, f"MATERIALS_{name.upper()}", []):
            textures = [ref[0] for group in groups for role, ref in group if role != "Occlusion"]
            result.append((material[:-len(".Material.Gbx")], textures))
    return result


def selected_block_definition(context):
    return module("props.block_definitions_panel").get_selected_block_definition(context)


def is_folder(block_def):
    return block_def.use_collection_icon or block_def.use_subfolder_icon


def export_counts(context):
    blocks = [block_def for block_def in context.scene.tmunlimiter_block_definitions if not is_folder(block_def)]
    return sum(1 for block_def in blocks if block_def.selected_for_export), len(blocks)
