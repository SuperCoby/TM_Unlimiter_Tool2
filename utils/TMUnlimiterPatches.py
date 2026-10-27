import bpy
import addon_utils
import functools
import re
from . import TMUnlimiter as tmu
from .BlockAnimation import wrap_plug_tree_animation
from ..properties.BlockDefinitionsProperties import extra_props
from ..panels.PT_BlockDefinitions import (
    draw_block_definition_item,
    filter_block_definition_items,
    wrap_panel_draw,
)

# Greffe nos ajouts sur tmunlimiter_blender_plugin (Tomek0055) à l'exécution, sans modifier ses
# fichiers, pour qu'il puisse rester identique à https://github.com/tomek0055/tmunlimiter_blender_plugin
# et être mis à jour : propriétés, liste et panneau "Block Definitions", nom de fichier par défaut
# à l'export, suppression du suffixe .001 dans les noms exportés. Tout fonctionne aussi s'il
# n'est pas installé.

PATCH_INTERVAL = 1.0


def _wrap_export_invoke(original):
    @functools.wraps(original)
    def invoke(self, context, event):
        # Nom de fichier par défaut = identifiant du block
        block_definition = tmu.selected_block_definition(context)
        if block_definition and block_definition.identifier:
            self.filepath = f"{block_definition.identifier}.Block.Gbx"
        return original(self, context, event)
    invoke.tmu_original = original
    return invoke


_SUFFIX = re.compile(r"^(.*?)(\.[0-9]{3})$")


def _wrap_plug_tree(original):
    # Correction du nom exporté : supprime le suffixe .001, .002, etc. On remplace, le temps
    # de l'appel, le mw_id() du GbxArchive pour ce seul nom.
    @functools.wraps(original)  # garde __name__ : mw_ref() s'en sert pour les validators
    def plug_tree_from_object(gbx, object, *args, **kwargs):
        name = object.name
        match = _SUFFIX.match(name)
        if not match:
            return original(gbx, object, *args, **kwargs)

        export_name = match.group(1)
        had_override = "mw_id" in gbx.__dict__
        previous = gbx.__dict__.get("mw_id")
        base_mw_id = gbx.mw_id

        def mw_id(mw_id="", *mw_args, **mw_kwargs):
            return base_mw_id(export_name if mw_id == name else mw_id, *mw_args, **mw_kwargs)

        gbx.mw_id = mw_id
        try:
            return original(gbx, object, *args, **kwargs)
        finally:
            if had_override:
                gbx.mw_id = previous
            else:
                del gbx.__dict__["mw_id"]
    plug_tree_from_object.tmu_original = original
    return plug_tree_from_object


def _reregister(cls):
    if getattr(cls, "is_registered", False):
        bpy.utils.unregister_class(cls)
        bpy.utils.register_class(cls)


def apply_patches():
    """Idempotent : appelé régulièrement, (re)greffe ce qui manque si tmunlimiter est chargé."""
    if not tmu.plugin_loaded():
        return

    panel_mod = tmu.module("props.block_definitions_panel")
    block_def_mod = tmu.module("block_definition")

    # Propriétés
    block_def_cls = block_def_mod.TMUnlimiter_BlockDefinition
    if getattr(block_def_cls, "is_registered", False):
        for name, prop in extra_props().items():
            if name not in block_def_cls.bl_rna.properties:
                setattr(block_def_cls, name, prop)

    # Liste : case à cocher + icône + filtre
    list_cls = panel_mod.TMUnlimiter_BlockDefinitionItem
    if not getattr(list_cls, "tmu_patched", False):
        list_cls.tmu_original_draw_item = list_cls.draw_item
        list_cls.draw_item = draw_block_definition_item
        list_cls.tmu_added_filter = "filter_items" not in list_cls.__dict__
        if list_cls.tmu_added_filter:
            list_cls.filter_items = filter_block_definition_items
            _reregister(list_cls)  # filter_items n'est pris en compte qu'à l'enregistrement
        list_cls.tmu_patched = True

    # Panneau : nos boutons aux mêmes places qu'avant
    panel_cls = panel_mod.TMUnlimiter_BlockDefinitionsPanel
    if not hasattr(panel_cls.draw, "tmu_original"):
        panel_cls.draw = wrap_panel_draw(panel_cls.draw)

    # Export simple : nom de fichier par défaut
    export_cls = panel_mod.TMUnlimiter_ExportBlockDefinition
    if not hasattr(export_cls.invoke, "tmu_original"):
        export_cls.invoke = _wrap_export_invoke(export_cls.invoke)

    # Noms exportés sans .001 + animation des objets (FuncTree, utils/BlockAnimation.py)
    tree_mod = tmu.module("plug_tree")
    if tree_mod is not None and not hasattr(tree_mod.plug_tree_from_object, "tmu_original"):
        original = tree_mod.plug_tree_from_object
        wrapped = _wrap_plug_tree(wrap_plug_tree_animation(original))
        wrapped.tmu_original = original  # remove_patches() restaure la fonction de tmunlimiter
        for mod in (tree_mod, tmu.module("block_definition"), tmu.module("plug_solid")):
            if mod is not None and getattr(mod, "plug_tree_from_object", None) is original:
                mod.plug_tree_from_object = wrapped


def remove_patches():
    panel_mod = tmu.module("props.block_definitions_panel")
    if panel_mod is not None:
        list_cls = panel_mod.TMUnlimiter_BlockDefinitionItem
        if getattr(list_cls, "tmu_patched", False):
            list_cls.draw_item = list_cls.tmu_original_draw_item
            if list_cls.tmu_added_filter:
                del list_cls.filter_items
                _reregister(list_cls)
            for attr in ("tmu_patched", "tmu_original_draw_item", "tmu_added_filter"):
                delattr(list_cls, attr)

        panel_cls = panel_mod.TMUnlimiter_BlockDefinitionsPanel
        if hasattr(panel_cls.draw, "tmu_original"):
            panel_cls.draw = panel_cls.draw.tmu_original

        export_cls = panel_mod.TMUnlimiter_ExportBlockDefinition
        if hasattr(export_cls.invoke, "tmu_original"):
            export_cls.invoke = export_cls.invoke.tmu_original

    tree_mod = tmu.module("plug_tree")
    if tree_mod is not None and hasattr(tree_mod.plug_tree_from_object, "tmu_original"):
        wrapped = tree_mod.plug_tree_from_object
        for mod in (tree_mod, tmu.module("block_definition"), tmu.module("plug_solid")):
            if mod is not None and getattr(mod, "plug_tree_from_object", None) is wrapped:
                mod.plug_tree_from_object = wrapped.tmu_original

    # Les données restent stockées dans les .blend : on ne retire que la définition des propriétés
    block_def_mod = tmu.module("block_definition")
    if block_def_mod is not None:
        block_def_cls = block_def_mod.TMUnlimiter_BlockDefinition
        if getattr(block_def_cls, "is_registered", False):
            for name in extra_props():
                if name in block_def_cls.bl_rna.properties and name not in getattr(block_def_cls, "__annotations__", {}):
                    delattr(block_def_cls, name)


def _patch_timer():
    # tmunlimiter peut être activé/désactivé/rechargé après nous : on regreffe si besoin
    try:
        apply_patches()
    except Exception as error:
        print(f"[TM Unlimiter Tool] tmunlimiter patches: {error}")
    return PATCH_INTERVAL


def _retry_enable_plugin():
    # Si tmunlimiter s'est chargé avant nous, son `import lzo` a échoué : on le réactive
    if tmu.PLUGIN in bpy.context.preferences.addons and not addon_utils.check(tmu.PLUGIN)[1]:
        addon_utils.enable(tmu.PLUGIN, default_set=False)
    return None


def register():
    bpy.app.timers.register(_retry_enable_plugin, first_interval=0.1)
    bpy.app.timers.register(_patch_timer, first_interval=0.2, persistent=True)


def unregister():
    for timer in (_patch_timer, _retry_enable_plugin):
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)
    remove_patches()
