import bpy
import os
import re
from bpy_extras.io_utils import ExportHelper
from traceback import print_exception
from ..utils import TMUnlimiter as tmu
from ..utils.Functions import addon_prefs
from ..utils.Detection import ensure_block_units

# Opérateurs ajoutés au panneau "TMUnlimiter - Block Definitions" de tmunlimiter_blender_plugin :
# export multiple, Auto Block Definition, entrées "dossier" (icône collection / sous-dossier).


class _PluginOperator:
    @classmethod
    def poll(cls, context):
        return tmu.plugin_loaded()


class TMU_OT_ToggleBlockDefinitionIcon(_PluginOperator, bpy.types.Operator):
    bl_label = "Toggle block definition icon"
    bl_description = "Turn the selected block definition into a collection folder for Export Multiple"
    bl_idname = "scene.tmu_toggle_block_definition_icon"

    def execute(self, context):
        selected_block_definition = tmu.selected_block_definition(context)
        if selected_block_definition:
            selected_block_definition.use_collection_icon = not selected_block_definition.use_collection_icon
        return {"FINISHED"}


class TMU_OT_ToggleBlockDefinitionSubfolder(_PluginOperator, bpy.types.Operator):
    bl_label = "Toggle block definition subfolder"
    bl_description = "Turn the selected block definition into a subfolder for Export Multiple"
    bl_idname = "scene.tmu_toggle_block_definition_subfolder"

    def execute(self, context):
        selected_block_definition = tmu.selected_block_definition(context)
        if selected_block_definition:
            selected_block_definition.use_subfolder_icon = not selected_block_definition.use_subfolder_icon
            if selected_block_definition.use_subfolder_icon:
                selected_block_definition.use_collection_icon = False
        return {"FINISHED"}


class TMU_OT_SelectAllBlockDefinitions(_PluginOperator, bpy.types.Operator):
    bl_label = "Select all block definitions"
    bl_idname = "scene.tmu_select_all_block_definitions"

    def execute(self, context):
        for block_def in context.scene.tmunlimiter_block_definitions:
            block_def.selected_for_export = True
        return {"FINISHED"}


class TMU_OT_DeselectAllBlockDefinitions(_PluginOperator, bpy.types.Operator):
    bl_label = "Deselect all block definitions"
    bl_idname = "scene.tmu_deselect_all_block_definitions"

    def execute(self, context):
        for block_def in context.scene.tmunlimiter_block_definitions:
            block_def.selected_for_export = False
        return {"FINISHED"}


class TMU_OT_ExportMultipleBlockDefinitions(bpy.types.Operator, ExportHelper):
    """Export multiple selected block definitions to separate *.Block.Gbx files"""

    bl_label = "Export Multiple"
    bl_idname = "scene.tmu_export_multiple_block_definitions"

    filename_ext = ""
    use_filter_folder = True

    @classmethod
    def poll(cls, context):
        if not tmu.plugin_loaded() or context.mode != "OBJECT":
            return False
        return tmu.export_counts(context)[0] > 0

    def execute(self, context):
        GbxArchive = tmu.module("blender_gbx").GbxArchive
        selected_blocks = [block_def for block_def in context.scene.tmunlimiter_block_definitions if block_def.selected_for_export]

        if not selected_blocks:
            self.report({'ERROR'}, "No blocks selected for export")
            return {'CANCELLED'}

        export_folder = self.filepath
        if not os.path.exists(export_folder):
            try:
                os.makedirs(export_folder)
            except Exception as e:
                self.report({'ERROR'}, f"Cannot create folder: {str(e)}")
                return {'CANCELLED'}

        exported_count = 0
        failed_exports = []

        current_collection_path = []

        for block_definition in selected_blocks:
            if block_definition.use_collection_icon:
                current_collection_path = [block_definition.identifier]
                full_folder_path = os.path.join(export_folder, *current_collection_path)
                if not os.path.exists(full_folder_path):
                    os.makedirs(full_folder_path)
                continue

            elif block_definition.use_subfolder_icon:
                if current_collection_path:
                    if len(current_collection_path) > 1:
                        current_collection_path[-1] = block_definition.identifier
                    else:
                        current_collection_path.append(block_definition.identifier)
                else:
                    current_collection_path = [block_definition.identifier]

                full_folder_path = os.path.join(export_folder, *current_collection_path)
                if not os.path.exists(full_folder_path):
                    os.makedirs(full_folder_path)
                continue

            try:
                if not self.validate_block_definition(block_definition):
                    failed_exports.append(f"{block_definition.identifier}: Validation failed")
                    continue

                gbx = GbxArchive(0x3f002000)
                gbx.context["depsgraph"] = context.evaluated_depsgraph_get()

                block_definition.archive(gbx)

                if current_collection_path:
                    collection_folder_path = os.path.join(export_folder, *current_collection_path)
                    filepath = os.path.join(collection_folder_path, f"{block_definition.identifier}.Block.Gbx")
                else:
                    filepath = os.path.join(export_folder, f"{block_definition.identifier}.Block.Gbx")

                gbx.do_save(filepath)
                exported_count += 1

            except Exception as error:
                failed_exports.append(f"{block_definition.identifier}: {str(error)}")
                print_exception(error)

        if exported_count > 0:
            self.report({'INFO'}, f"Successfully exported {exported_count} blocks to {export_folder}")

        if failed_exports:
            for failure in failed_exports:
                self.report({'WARNING'}, f"Failed: {failure}")

        return {'FINISHED'}

    def validate_block_definition(self, block_definition):
        """Valider une définition de bloc"""
        validations = [
            block_definition.validate_identifier()[0],
            block_definition.validate_author()[0],
            block_definition.validate_variants()[0],
            block_definition.validate_icon()[0],
            block_definition.validate_block_units()[0]
        ]
        return all(validations)

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


keywords_values = {
    "Checkpoint": "checkpoint",
    "Finish": "finish",
    "Multilap": "multilap",
    "Start": "start"
}


def name_kind(name):
    """"ground" / "air" / None d'après les mots du nom (séparés par _ . - ou espace),
    ex. "Block_Ground_Col" -> "ground", "Block_Air.003" -> "air" ("Stairs" ne compte pas)."""
    words = set(re.split(r"[_.\-\s]+", name.lower()))
    if words & {"ground", "grass"}:
        return "ground"
    if "air" in words:
        return "air"
    return None


def is_trigger_object(obj):
    return "trigger" in obj.name.lower()


def pick_ground_air(objects):
    """(ground, air) parmi des objets triés par nom : d'après leur nom, sinon le même pour les deux."""
    ground = next((obj for obj in objects if name_kind(obj.name) == "ground"), None)
    air = next((obj for obj in objects if name_kind(obj.name) == "air"), None)
    if ground is None and air is None and objects:
        ground = air = objects[0]
    return ground or air, air or ground


def select_objects_with_trigger(collection):
    """Trouve les objets trigger pour les variations Ground et Air (un seul trigger = les deux)"""
    triggers = sorted((obj for obj in collection.all_objects if obj.type == 'MESH' and is_trigger_object(obj)),
                      key=lambda obj: obj.name)
    ground_trigger, air_trigger = pick_ground_air(triggers)
    for obj in (ground_trigger, air_trigger):
        if obj:
            obj.select_set(True)
    return ground_trigger, air_trigger


class TMU_OT_AutoBlockDefinition(_PluginOperator, bpy.types.Operator):
    bl_label = "Auto Block Definition"
    bl_description = "Create a block definition from the active collection (variations, spawns, triggers, waypoint type)"
    bl_idname = "scene.tmu_auto_block_definition"

    @staticmethod
    def is_valid_collection(collection):
        return not collection.hide_viewport and not collection.name.startswith("Exclude_")

    @staticmethod
    def add_block_definition(collection_name, custom_author):
        try:
            block_definition = bpy.context.scene.tmunlimiter_block_definitions.add()
            block_definition.identifier = collection_name
            block_definition.author = custom_author
        except Exception as e:
            pass

    @staticmethod
    def find_empty_in_collection(collection):
        """Spawns : empties sans enfant de la collection puis de ses sous-collections
        (hors block units, affichés en cube)"""
        empty_objects = []
        for obj in list(collection.objects) + list(collection.all_objects):
            if obj.type == 'EMPTY' and not obj.children and obj.empty_display_type != 'CUBE' \
                    and obj not in empty_objects:
                empty_objects.append(obj)
        return empty_objects

    @staticmethod
    def find_variation_objects(collection):
        """Modèles Ground et Air : objets racines de la hiérarchie (sans parent dans la
        collection, enfants exportés avec eux), hors triggers, d'après "Ground"/"Air" dans le nom"""
        objects = set(collection.all_objects)
        roots = sorted(
            (obj for obj in objects
             if obj.type == 'MESH' and (obj.parent is None or obj.parent not in objects)
             and not is_trigger_object(obj)
             and not obj.unlimiter_object_settings.exclude_from_export),
            key=lambda obj: obj.name,
        )
        ground_objects = [obj for obj in roots if name_kind(obj.name) == "ground"]
        air_objects = [obj for obj in roots if name_kind(obj.name) == "air"]
        return ground_objects, air_objects

    @staticmethod
    def update_waypoint_type(collection):
        def check_keyword(name):
            for keyword in keywords_values:
                if keyword.lower() in name.lower():
                    return keywords_values[keyword]
            return None

        def recursive_check(collection):
            waypoint_type = check_keyword(collection.name)
            if waypoint_type:
                return waypoint_type

            for obj in collection.objects:
                waypoint_type = check_keyword(obj.name)
                if waypoint_type:
                    return waypoint_type

            for sub_collection in collection.children:
                waypoint_type = recursive_check(sub_collection)
                if waypoint_type:
                    return waypoint_type

            return None

        waypoint_type = recursive_check(collection)
        if waypoint_type:
            bpy.context.scene.tmunlimiter_block_definitions[-1].waypoint_type = waypoint_type

    @staticmethod
    def find_block_collection(context):
        """Collection active ; si c'est la Scene Collection, celle de l'objet actif"""
        collection = context.view_layer.active_layer_collection.collection
        if collection == context.scene.collection and context.active_object:
            for user_collection in context.active_object.users_collection:
                if user_collection != context.scene.collection:
                    return user_collection
        return collection

    @staticmethod
    def find_default_model(collection):
        """Sans "ground"/"air" dans les noms : premier mesh racine de la collection (sous-collections
        comprises), de préférence avec "Export collision" coché"""
        meshes = sorted(
            (obj for obj in collection.all_objects
             if obj.type == 'MESH' and obj.parent is None
             and not obj.unlimiter_object_settings.exclude_from_export),
            key=lambda obj: obj.name,
        )
        with_collision = [obj for obj in meshes if obj.unlimiter_object_settings.can_export_collision]
        return (with_collision or meshes or [None])[0]

    def execute(self, context):
        selected_collection = self.find_block_collection(context)
        if selected_collection == context.scene.collection:
            self.report({'ERROR'}, "Select the block's collection in the Outliner (or an object of the block)")
            return {"CANCELLED"}
        if selected_collection and self.is_valid_collection(selected_collection):
            custom_author = addon_prefs().block_author
            self.add_block_definition(selected_collection.name, custom_author)
            try:
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
            except RuntimeError:
                pass  # pas de fenêtre (Blender en arrière-plan)
            new_block_index = len(bpy.context.scene.tmunlimiter_block_definitions) - 1
            bpy.context.scene.tmunlimiter_selected_block_definition_index = new_block_index
            new_block_definition = bpy.context.scene.tmunlimiter_block_definitions[new_block_index]
            new_block_definition.selected_variant_type = 'air'
            bpy.ops.scene.tmunlimiter_add_variation()
            new_block_definition.selected_variant_type = 'ground'
            bpy.ops.scene.tmunlimiter_add_variation()
            ground_variation = new_block_definition.variants_classic_default.ground_variations[0]
            ground_variation.name = "Default"
            air_variation = new_block_definition.variants_classic_default.air_variations[0]
            air_variation.name = "Default"

            empty_objects = self.find_empty_in_collection(selected_collection)
            if empty_objects:
                named = sorted(empty_objects, key=lambda obj: obj.name)
                ground_spawn = next((obj for obj in named if name_kind(obj.name) == "ground"), None)
                air_spawn = next((obj for obj in named if name_kind(obj.name) == "air"), None)
                if ground_spawn is None and air_spawn is None:
                    # Pas de "Ground"/"Air" dans les noms : ordre de la collection, comme avant
                    ground_spawn = empty_objects[0]
                    air_spawn = empty_objects[1] if len(empty_objects) > 1 else empty_objects[0]
                new_block_definition.ground_spawn_location_object = ground_spawn or air_spawn
                new_block_definition.air_spawn_location_object = air_spawn or ground_spawn

            ground_objects, air_objects = self.find_variation_objects(selected_collection)

            # Un seul côté trouvé : le même modèle pour Ground et Air
            if ground_objects or air_objects:
                new_block_definition.variants_classic_default.ground_variations[0].model = (ground_objects or air_objects)[0]
                new_block_definition.variants_classic_default.air_variations[0].model = (air_objects or ground_objects)[0]

            if not ground_objects and not air_objects:
                default_model = self.find_default_model(selected_collection)

                if default_model:
                    new_block_definition.variants_classic_default.ground_variations[0].model = default_model
                    new_block_definition.variants_classic_default.air_variations[0].model = default_model
                else:
                    self.report({'WARNING'}, f'No mesh found in collection "{selected_collection.name}": no model, no block units')

            bpy.ops.object.select_all(action='DESELECT')

            for obj in ground_objects + air_objects:
                obj.select_set(True)

            self.update_waypoint_type(selected_collection)

            ground_trigger, air_trigger = select_objects_with_trigger(selected_collection)

            if ground_trigger:
                new_block_definition.variants_classic_default.ground_variations[0].trigger = ground_trigger

            if air_trigger:
                new_block_definition.variants_classic_default.air_variations[0].trigger = air_trigger

            self.fill_block_units(new_block_definition, context)

        return {"FINISHED"}

    @staticmethod
    def fill_block_units(block_definition, context):
        """Ajoute aux Block Units (Ground / Air) les block units occupés par le modèle de chaque
        variation, en créant les empties manquants (grille de l'environnement de Detection Units).
        Retourne le nombre de block units ajoutés."""
        BlockUnit = tmu.module("block_unit").TMUnlimiter_BlockUnit

        def is_valid(obj):
            return BlockUnit.static_object_validate(obj)[0]

        def order(empty):
            # Par couche, puis X, puis Y (comme dans la liste de tmunlimiter)
            offset = BlockUnit.static_calculate_offset(empty)
            return (offset[1], offset[2], offset[0])

        depsgraph = context.evaluated_depsgraph_get()
        environment = context.scene.block_units_environment
        added = 0
        for unit_type in ("ground", "air"):
            model = getattr(block_definition.variants_classic_default, f"{unit_type}_variations")[0].model
            if model is None:
                continue

            # Le modèle et ses enfants exportés (comme à l'export de tmunlimiter)
            meshes = [obj for obj in (model, *model.children_recursive)
                      if obj.type == 'MESH' and not obj.unlimiter_object_settings.exclude_from_export]
            if not meshes:
                continue

            occupied = ensure_block_units(meshes, depsgraph, environment, is_valid)

            block_units = getattr(block_definition, f"{unit_type}_block_units")
            existing = {block_unit.calculate_offset() for block_unit in block_units if block_unit.object}
            for empty in sorted(occupied, key=order):
                offset = BlockUnit.static_calculate_offset(empty)
                if offset in existing:
                    continue
                existing.add(offset)
                block_units.add().object = empty
                added += 1

        return added


classes = (
    TMU_OT_ToggleBlockDefinitionIcon,
    TMU_OT_ToggleBlockDefinitionSubfolder,
    TMU_OT_SelectAllBlockDefinitions,
    TMU_OT_DeselectAllBlockDefinitions,
    TMU_OT_ExportMultipleBlockDefinitions,
    TMU_OT_AutoBlockDefinition,
)
