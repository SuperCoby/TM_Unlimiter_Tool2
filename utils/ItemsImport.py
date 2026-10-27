import bpy
import math
import os
import glob
from pathlib import Path
from .Constants import WAYPOINTS
from .Functions import (ireplace, fix_slash)
from .Import import import_item_gbx as parse_item_gbx, import_solid_gbx as parse_solid_gbx, import_block_gbx as parse_block_gbx
from .BlenderObjects import create_collection_in, move_obj_to_coll

def import_items_gbx_folder(folder_path: str):
    folder_path = fix_slash(folder_path)
    parts = folder_path.split("/")
    base_coll = create_collection_in(bpy.context.collection, parts[len(parts) - 2])
    # Tous les fichiers puis filtre sans tenir compte de la casse : sous Linux/macOS
    # "*.gbx" ne trouverait pas les "Foo.Item.Gbx" (glob y est sensible à la casse)
    for item_path in glob.iglob(glob.escape(folder_path) + '**/*', recursive=True):
        item_path = fix_slash(item_path)
        if not item_path.lower().endswith(".gbx"):
            continue

        name = Path(item_path).stem
        name = ireplace(".solid", "", ireplace(".item", "", name))

        path = item_path.replace(folder_path, "")
        coll = base_coll
        for part in path.split("/"):
            if part.lower().endswith(".gbx"):
                break

            new_name = coll.name+"_"+part
            if new_name in coll.children:
                coll = coll.children[new_name]
            else:
                coll = create_collection_in(coll, new_name)

        import_item_gbx(item_path, name, coll)

def import_item_gbx(item_path: str, name: str = None, coll: bpy.types.Collection = None):
    if coll == None:
        coll = bpy.context.collection

    if name == None:
        name = Path(item_path).stem
        name = ireplace(".solid", "", ireplace(".item", "", name))

    if item_path.lower().endswith(".block.gbx"):
        # TMUnlimiter block: its own collection + object hierarchy, no clean-up/renaming
        try:
            parse_block_gbx(item_path, coll)
        except Exception as e:
            return str(e)
        return None

    try:
        if item_path.lower().endswith(".solid.gbx"):
            objs = parse_solid_gbx(item_path)  # TMNF/TMUF .Solid.Gbx: visual + collision-only
        else:
            objs = [parse_item_gbx(item_path)]
    except Exception as e:
        return str(e)

    _clean_up_imported_item_gbx(objs, name, coll)

    return None

def _clean_up_imported_item_gbx(objs: list[bpy.types.Object], item_name: str, dest_coll: bpy.types.Collection):
    coll = create_collection_in(dest_coll, item_name)

    for i, obj in enumerate(objs):
        obj:bpy.types.Object = obj
        move_obj_to_coll(obj, coll)
        # 1er objet = nom de l'item ; les suivants (collision d'un .Solid.Gbx) gardent leur suffixe
        obj.name = item_name if i == 0 else f"{item_name}_Collision"



        # fix UV
        if len(obj.data.uv_layers) > 0:
            obj.data.uv_layers[0].name = "BaseMaterial"

        # auto smooth
        obj.data.polygons.foreach_set('use_smooth',  [True] * len(obj.data.polygons))
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth_by_angle(angle=math.pi/6)

    return None
