import bpy
import fnmatch
import functools
from ..utils import TMUnlimiter as tmu
from ..operators.OT_BlockDefinitions import (
    TMU_OT_ToggleBlockDefinitionIcon,
    TMU_OT_ToggleBlockDefinitionSubfolder,
    TMU_OT_SelectAllBlockDefinitions,
    TMU_OT_DeselectAllBlockDefinitions,
    TMU_OT_ExportMultipleBlockDefinitions,
    TMU_OT_AutoBlockDefinition,
)

# Dessin de nos ajouts dans le panneau "TMUnlimiter - Block Definitions" de tmunlimiter_blender_plugin
# (greffé par utils/TMUnlimiterPatches.py) : case "export" + icône dans la liste, filtre de la
# liste, et nos boutons aux mêmes places qu'avant dans le panneau.


# Décalage par niveau de dossier dans la liste (espace de layout.separator)
INDENT_FACTOR = 1.0


def is_folder(block_def):
    return getattr(block_def, "use_collection_icon", False) or getattr(block_def, "use_subfolder_icon", False)


def block_definition_tree(block_definitions):
    """[(niveau, masqué)] de chaque entrée : même arborescence que les dossiers créés par
    Export Multiple (une entrée "Collection" ouvre un dossier, une entrée "Subfolder" un
    sous-dossier dedans, les blocks qui suivent vont dans le dernier dossier ouvert).
    Une entrée est masquée si un de ses dossiers parents est plié."""
    tree = []
    path_length = 0
    collapsed = [False, False]  # dossier de niveau 0, sous-dossier de niveau 1
    for block_def in block_definitions:
        if getattr(block_def, "use_collection_icon", False):
            level, path_length = 0, 1
        elif getattr(block_def, "use_subfolder_icon", False):
            level = 1 if path_length else 0
            path_length = level + 1
        else:
            level = path_length
        hidden = any(collapsed[:min(level, 2)])
        if is_folder(block_def):
            collapsed[level] = getattr(block_def, "tmu_collapsed", False)
            if level == 0:
                collapsed[1] = False
        tree.append((level, hidden))
    return tree


def draw_block_definition_item(self, context, layout, data, block_definition, icon, active_data, active_propname, index):
    if hasattr(block_definition, "selected_for_export"):
        layout.prop(block_definition, "selected_for_export", text="")
    # Décalage selon le dossier d'export (pas en tri alphabétique : l'ordre n'a plus de sens)
    tree_mode = not self.use_filter_sort_alpha
    if tree_mode:
        level = block_definition_tree(context.scene.tmunlimiter_block_definitions)[index][0]
        if level:
            layout.separator(factor=INDENT_FACTOR * level)
    if getattr(block_definition, "use_collection_icon", False):
        icon = "OUTLINER_COLLECTION"
    elif getattr(block_definition, "use_subfolder_icon", False):
        icon = "FILE_FOLDER"
    else:
        icon = "MATCUBE"
    layout.label(text=block_definition.identifier, icon=icon)
    # Flèche plier/déplier des dossiers, à droite de la ligne
    if is_folder(block_definition) and tree_mode and hasattr(block_definition, "tmu_collapsed"):
        collapsed = block_definition.tmu_collapsed
        arrow = layout.row()
        arrow.alignment = "RIGHT"
        arrow.prop(block_definition, "tmu_collapsed", text="", emboss=False,
                   icon="RIGHTARROW" if collapsed else "DOWNARROW_HLT")


def filter_block_definition_items(self, context, data, propname):
    """Filtre et trie les éléments de la liste"""
    block_definitions = getattr(data, propname)

    flt_flags = []
    flt_neworder = []

    if not block_definitions:
        return flt_flags, flt_neworder

    flt_flags = [self.bitflag_filter_item] * len(block_definitions)

    if self.filter_name:
        pattern = self.filter_name.lower()
        if not ('*' in pattern or '?' in pattern):
            pattern = f"*{pattern}*"

        for i, block_def in enumerate(block_definitions):
            if not fnmatch.fnmatch(block_def.identifier.lower(), pattern):
                flt_flags[i] = 0
    elif not self.use_filter_sort_alpha:
        # Contenu des dossiers pliés masqué (pas pendant une recherche ni en tri alphabétique)
        for i, (_level, hidden) in enumerate(block_definition_tree(block_definitions)):
            if hidden:
                flt_flags[i] = 0

    if self.use_filter_sort_alpha:
        items_with_indices = [(i, block_def.identifier.lower()) for i, block_def in enumerate(block_definitions)]

        items_with_indices.sort(key=lambda x: x[1], reverse=self.use_filter_sort_reverse)

        flt_neworder = [item[0] for item in items_with_indices]

    return flt_flags, flt_neworder


# Champs du panneau de Tomek à ne pas afficher (la valeur reste stockée et exportée)
HIDDEN_PROPERTIES = {
    "pre_light_gen_tile_count",
}


class _PanelLayout:
    """Layout transmis au draw() de Tomek : relaie tout au vrai UILayout, mais insère nos
    boutons aux mêmes endroits qu'avant (colonne à côté de la liste, sous la liste, export)
    et masque les champs de HIDDEN_PROPERTIES."""

    def __init__(self, layout, state, top=False):
        object.__setattr__(self, "_layout", layout)
        object.__setattr__(self, "_state", state)
        object.__setattr__(self, "_top", top)

    def __getattr__(self, name):
        return getattr(self._layout, name)

    def __setattr__(self, name, value):
        setattr(self._layout, name, value)

    def _wrap(self, layout):
        return _PanelLayout(layout, self._state)

    def row(self, *args, **kwargs):
        if self._top and self._state.pop("pending_select_rows", False):
            _draw_select_rows(self._layout, self._state["context"])
        return self._wrap(self._layout.row(*args, **kwargs))

    def column(self, *args, **kwargs):
        return self._wrap(self._layout.column(*args, **kwargs))

    def box(self, *args, **kwargs):
        return self._wrap(self._layout.box(*args, **kwargs))

    def split(self, *args, **kwargs):
        return self._wrap(self._layout.split(*args, **kwargs))

    def prop(self, data, property, *args, **kwargs):
        if property in HIDDEN_PROPERTIES:
            return None
        return self._layout.prop(data, property, *args, **kwargs)

    def operator(self, operator, *args, **kwargs):
        panel_mod = tmu.module("props.block_definitions_panel")

        if self._top and operator == panel_mod.TMUnlimiter_ExportBlockDefinition.bl_idname:
            row = self._layout.row()
            props = row.operator(operator, text="Export Single", icon="EXPORT")
            _draw_export_multiple(row, self._state["context"])
            return props

        props = self._layout.operator(operator, *args, **kwargs)

        if operator == panel_mod.TMUnlimiter_MoveBlockDefinitionDownwards.bl_idname:
            self._layout.operator(TMU_OT_ToggleBlockDefinitionIcon.bl_idname, text="", icon="OUTLINER_COLLECTION")
            self._layout.operator(TMU_OT_ToggleBlockDefinitionSubfolder.bl_idname, text="", icon="FILE_FOLDER")
            self._layout.operator(TMU_OT_AutoBlockDefinition.bl_idname, text="", icon="AUTO")
            self._state["pending_select_rows"] = True

        return props


class _PanelSelf:
    # Remplace `self` pour le draw() de Tomek : seul `layout` change
    def __init__(self, panel, layout):
        object.__setattr__(self, "_panel", panel)
        object.__setattr__(self, "layout", layout)

    def __getattr__(self, name):
        return getattr(self._panel, name)


def _draw_select_rows(layout, context):
    selected_count, total_count = tmu.export_counts(context)
    row = layout.row()
    row.label(text=f"Selected for export: {selected_count}/{total_count}")

    row = layout.row()
    row.operator(TMU_OT_SelectAllBlockDefinitions.bl_idname, text="Select All")
    row.operator(TMU_OT_DeselectAllBlockDefinitions.bl_idname, text="Deselect All")


def _draw_export_multiple(row, context):
    selected_count = tmu.export_counts(context)[0]
    if selected_count > 0:
        row.operator(TMU_OT_ExportMultipleBlockDefinitions.bl_idname, text=f"Export {selected_count} Blocks", icon="PACKAGE")
    else:
        col = row.column()
        col.enabled = False
        col.operator(TMU_OT_ExportMultipleBlockDefinitions.bl_idname, text="Export Multiple", icon="PACKAGE")


def wrap_panel_draw(original):
    @functools.wraps(original)
    def draw(self, context):
        state = {"context": context}
        original(_PanelSelf(self, _PanelLayout(self.layout, state, top=True)), context)
        # Liste vide / aucun block sélectionné : le draw() de Tomek s'arrête avant l'export
        if state.pop("pending_select_rows", False):
            _draw_select_rows(self.layout, context)
    draw.tmu_original = original
    return draw
