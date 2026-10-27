import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

# Coins et faces (quads) d'un cube unitaire centré, pour construire le BVH des block units
_BOX_SIGNS = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
              (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
_BOX_FACES = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
              (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]


def _world_geometry(objects, depsgraph):
    """Vertices (Nx3, world space, modifiers applied) and triangles (Mx3) of all given meshes."""
    all_co, all_tris, offset = [], [], 0
    for obj in objects:
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()
        if hasattr(mesh, "calc_loop_triangles"):
            mesh.calc_loop_triangles()
        co = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
        mesh.vertices.foreach_get("co", co)
        mw = np.array(obj_eval.matrix_world)
        co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        tris = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int64)
        mesh.loop_triangles.foreach_get("vertices", tris)
        all_co.append(co)
        all_tris.append(tris.reshape(-1, 3) + offset)
        offset += len(co)
        obj_eval.to_mesh_clear()
    return np.concatenate(all_co), np.concatenate(all_tris)


def detect_block_units(meshes, empties, depsgraph, margin=0.0):
    """Empties (block units, cubes) occupés par la géométrie des meshes donnés, dans l'ordre de `empties`."""
    verts, tris = _world_geometry(meshes, depsgraph)
    if not len(verts):
        return []
    mesh_min, mesh_max = verts.min(axis=0), verts.max(axis=0)

    # Boîte de chaque empty, réduite de 1 mm (+ la marge) sur chaque côté : une géométrie qui
    # touche juste la frontière d'un block voisin ne le compte pas. On ignore les boîtes hors
    # de la bbox du mesh.
    candidates = []  # (empty, demi-taille locale, matrice inverse, bbox min, bbox max)
    box_verts, box_faces = [], []
    for empty in empties:
        mw = empty.matrix_world
        scale = mw.to_scale()
        if any(abs(s) < 1e-9 for s in scale):
            continue
        size = empty.empty_display_size
        half = np.array([max(size - (0.001 + margin) / abs(s), 0.0) for s in scale])
        corners = np.array([tuple(mw @ Vector(np.multiply(sign, half))) for sign in _BOX_SIGNS])
        lo, hi = corners.min(axis=0), corners.max(axis=0)
        if np.any(hi < mesh_min) or np.any(lo > mesh_max):
            continue
        base = len(box_verts)
        box_verts.extend(corners.tolist())
        box_faces.extend([tuple(base + i for i in face) for face in _BOX_FACES])
        candidates.append((empty, half, np.array(mw.inverted()), lo, hi))

    hit = set()
    mesh_bvh = BVHTree.FromPolygons(verts.tolist(), tris.tolist()) if len(tris) else None

    # 1) Un triangle du mesh traverse une face de la boîte (test exact triangle/triangle)
    if candidates and mesh_bvh:
        box_bvh = BVHTree.FromPolygons(box_verts, box_faces)
        for _mesh_tri, box_face in mesh_bvh.overlap(box_bvh):
            hit.add(box_face // len(_BOX_FACES))

    # 2) Géométrie entièrement contenue dans la boîte (aucune face traversée) : test des vertices
    for i, (empty, half, inv, lo, hi) in enumerate(candidates):
        if i in hit:
            continue
        inside_aabb = np.all((verts >= lo) & (verts <= hi), axis=1)
        if not inside_aabb.any():
            continue
        local = verts[inside_aabb] @ inv[:3, :3].T + inv[:3, 3]
        if np.any(np.all(np.abs(local) <= half, axis=1)):
            hit.add(i)

    # 3) Boîte entièrement à l'intérieur d'un volume fermé, dont les faces sont pile sur les
    #    frontières du block (ex. un block plein de 32x32) : aucune face traversée ni vertex dedans
    if mesh_bvh:
        for i, (empty, half, inv, lo, hi) in enumerate(candidates):
            if i not in hit and _is_inside_volume(mesh_bvh, Vector(empty.matrix_world.translation)):
                hit.add(i)

    return [candidates[i][0] for i in sorted(hit)]


_RAY_DIRECTIONS = [Vector(d) for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))]


def _count_ray_hits(bvh, origin, direction, max_hits=1000):
    hits = 0
    while hits < max_hits:
        location, _normal, _index, _distance = bvh.ray_cast(origin, direction)
        if location is None:
            break
        hits += 1
        origin = location + direction * 1e-4
    return hits


def _is_inside_volume(bvh, point):
    """Point à l'intérieur d'un volume fermé : un rayon dans chacune des 6 directions touche
    le mesh un nombre impair de fois (un plan ouvert ne le touche que dans une direction)."""
    return all(_count_ray_hits(bvh, point, direction) % 2 == 1 for direction in _RAY_DIRECTIONS)


def grid_settings(environment):
    """(start_location, scale, step_x, step_y, step_z) de la grille de block units d'un environnement.
    scale = demi-taille d'un block ; l'espacement réel en Z vaut 2 * step_z (voir setup_block_units)."""
    if environment in ['RALLY', 'BAY', 'STADIUM']:
        return (16, 16, 4), (16, 16, 4), 32, 32, 4
    elif environment == 'COAST':
        return (8, 8, 2), (8, 8, 2), 16, 16, 2
    elif environment == 'ISLAND':
        return (32, 32, 1), (32, 32, 1), 64, 64, 1
    elif environment in ['SNOW', 'DESERT']:
        return (16, 16, 8), (16, 16, 8), 32, 32, 8
    return (16, 16, 4), (16, 16, 4), 32, 32, 4


def ensure_block_units(meshes, depsgraph, environment, is_valid=lambda obj: True):
    """Block units (empties) occupés par les meshes, sur la grille de l'environnement : réutilise
    ceux qui existent déjà à la bonne place, crée les manquants (comme le bouton Import de
    Detection Units) et ne garde que ceux réellement occupés.
    Retourne les block units occupés."""
    start_location, scale, step_x, step_y, step_z = grid_settings(environment)
    size = (2 * scale[0], 2 * scale[1], 2 * scale[2])

    verts, _tris = _world_geometry(meshes, depsgraph)
    if not len(verts):
        return []
    mesh_min, mesh_max = verts.min(axis=0), verts.max(axis=0)

    # Cellules couvertes par la bbox du mesh (indices >= 0 : tmunlimiter refuse les positions négatives)
    lo = [max(int(np.floor(mesh_min[k] / size[k])), 0) for k in range(3)]
    hi = [int(np.floor(mesh_max[k] / size[k])) for k in range(3)]

    existing = {}
    for obj in bpy.context.scene.objects:
        if obj.type == 'EMPTY' and obj.empty_display_type == 'CUBE' and is_valid(obj):
            existing[tuple(round(v, 3) for v in obj.location)] = obj

    block_units_collection = None
    candidates, created = [], []
    for layer in range(lo[2], hi[2] + 1):
        for row in range(lo[1], hi[1] + 1):
            for col in range(lo[0], hi[0] + 1):
                location = (scale[0] + col * size[0], scale[1] + row * size[1], scale[2] + layer * size[2])
                empty = existing.get(tuple(round(v, 3) for v in location))
                if empty is None:
                    if block_units_collection is None:
                        block_units_collection = create_or_get_collection("BlockUnits", color_tag='COLOR_03')
                    collection = create_or_get_collection(f"y{layer}", parent=block_units_collection)
                    empty = add_empty_cube(f"{row},{layer},{col}", location, scale, collection)
                    created.append(empty)
                candidates.append(empty)

    if created:
        bpy.context.view_layer.update()  # matrix_world des nouveaux empties

    hit = detect_block_units(meshes, candidates, depsgraph)

    # Les empties créés pour rien (cellule de la bbox mais pas occupée) sont supprimés
    hit_set = set(hit)
    for empty in created:
        if empty not in hit_set:
            bpy.data.objects.remove(empty, do_unlink=True)

    return hit


def create_or_get_collection(name, parent=None, color_tag=None):
    collection = bpy.data.collections.get(name)
    if not collection:
        collection = bpy.data.collections.new(name)
        if parent:
            parent.children.link(collection)
        else:
            bpy.context.scene.collection.children.link(collection)
    if color_tag:
        collection.color_tag = color_tag
    return collection

def add_empty_cube(name, location, scale, collection):
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = 'CUBE'
    empty.location = location
    empty.scale = scale
    collection.objects.link(empty)
    return empty

def add_multiple_empties(start_location, scale, rows, columns, step_x, step_y, collection, z_position, step_z):
    for row in range(rows):
        for col in range(columns):
            name = f"{row},{z_position},{col}"
            location = (
                start_location[0] + col * step_x, 
                start_location[1] + row * step_y, 
                start_location[2] + z_position * step_z
            )
            add_empty_cube(name, location, scale, collection)

def setup_block_units(rows, columns, start_location, scale, step_x, step_y, step_z, parent_collection, num_collections, z_offset_increment):
    for i in range(num_collections):
        collection_name = f"y{i}"
        z_offset = i * z_offset_increment
        start_location_z = start_location[2] + (z_offset * step_z)
        collection = create_or_get_collection(collection_name, parent=parent_collection)
        add_multiple_empties(
            start_location=(start_location[0], start_location[1], start_location_z), 
            scale=scale,
            rows=rows,
            columns=columns,
            step_x=step_x,
            step_y=step_y,
            collection=collection,
            z_position=z_offset,
            step_z=step_z
        )
