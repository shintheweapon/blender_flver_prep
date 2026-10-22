# Copies an armature and its meshes into a new collection, converted into the
# axes FbxImporter reads (raw mesh data, Y up, no object transforms); no UI

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

import bpy
from bpy_extras.io_utils import axis_conversion
from mathutils import Matrix

# Suffix of every copied object, mesh, armature and of the collection
SUFFIX = "_fs"
# Custom property on the collection naming the armature it was made from
SOURCE_KEY = "fs_fbx_source"
# Custom properties on the collection recording the options it was made with
MIRROR_Z_KEY = "fs_fbx_mirror_z"
FLIP_FACES_KEY = "fs_fbx_flip_faces"
# Custom property on each collection recreated inside the copy collection,
# naming the armature it was made for, so a re-run can remove it
PART_OF_KEY = "fs_fbx_part_of"

# A chain of collections from the scene's root collection down
CollectionPath = Tuple[bpy.types.Collection, ...]


@dataclass
class PreparedCopy:
    """What :func:`prepare_copy` made."""
    collection: bpy.types.Collection
    armature: bpy.types.Object
    meshes: List[bpy.types.Object] = field(default_factory=list)


def conversion_matrix(mirror_z: bool) -> Matrix:
    """
    Build the matrix from Blender world space to the space FbxImporter reads.

    Parameters
    ----------
    mirror_z : bool
        Also negate Z, as FbxImporter's Mirror Z option does.

    Returns
    -------
    mathutils.Matrix
        4x4 matrix: (x, y, z) to (x, z, -y), the axis conversion of Blender's
        FBX export with Forward -Z and Up Y; with ``mirror_z``, (x, z, y).
    """
    matrix = axis_conversion(to_forward='-Z', to_up='Y').to_4x4()
    if mirror_z:
        matrix = Matrix.Diagonal((1.0, 1.0, -1.0, 1.0)) @ matrix
    return matrix


def armature_meshes(armature_obj: bpy.types.Object,
                    objects: Iterable[bpy.types.Object]) -> List[bpy.types.Object]:
    """
    List the meshes that belong to an armature.

    Parameters
    ----------
    armature_obj : bpy.types.Object
        The armature object.
    objects : iterable of bpy.types.Object
        Objects to look through, usually the scene's.

    Returns
    -------
    list of bpy.types.Object
        Mesh objects parented to the armature or with an Armature modifier
        that targets it, sorted by name.
    """
    meshes = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        targets = any(mod.type == 'ARMATURE' and mod.object == armature_obj
                      for mod in obj.modifiers)
        if obj.parent == armature_obj or targets:
            meshes.append(obj)
    return sorted(meshes, key=lambda obj: obj.name)


def flipped_corner_order(loop_starts: Iterable[int], loop_totals: Iterable[int]) -> List[int]:
    """
    Map each corner after ``Mesh.flip_normals`` to the corner it came from.

    ``flip_normals`` keeps each face's first corner and reverses the rest.

    Parameters
    ----------
    loop_starts : iterable of int
        First corner index of each face.
    loop_totals : iterable of int
        Number of corners of each face.

    Returns
    -------
    list of int
        For each corner index after the flip, its index before the flip.
    """
    order = []
    for start, total in zip(loop_starts, loop_totals):
        order.extend(start + (total - k) % total for k in range(total))
    return order


def collection_paths(scene: bpy.types.Scene, obj: bpy.types.Object) -> List[CollectionPath]:
    """
    List the chains of collections that lead to an object.

    Parameters
    ----------
    scene : bpy.types.Scene
        The scene whose collections are searched.
    obj : bpy.types.Object
        The object to find.

    Returns
    -------
    list of tuple of bpy.types.Collection
        One chain per collection holding ``obj``, from a child of the scene's
        root collection down to that collection, depth first in child order.
        An object linked in the root collection itself has the empty chain.
    """
    paths: List[CollectionPath] = [()] if obj.name in scene.collection.objects else []

    def walk(parent: bpy.types.Collection, path: CollectionPath) -> None:
        for child in parent.children:
            child_path = path + (child,)
            if obj.name in child.objects:
                paths.append(child_path)
            walk(child, child_path)

    walk(scene.collection, ())
    return paths


def shared_top(paths: Iterable[CollectionPath]) -> CollectionPath:
    """
    Find the collections every chain starts with.

    Parameters
    ----------
    paths : iterable of tuple of bpy.types.Collection
        Chains from :func:`collection_paths`.

    Returns
    -------
    tuple of bpy.types.Collection
        The longest chain that starts every one of ``paths``; empty when they
        share nothing or there are none.
    """
    paths = list(paths)
    if not paths:
        return ()
    common = list(paths[0])
    for path in paths[1:]:
        size = 0
        while size < min(len(common), len(path)) and common[size] == path[size]:
            size += 1
        del common[size:]
    return tuple(common)


def _copy_collections(scene: bpy.types.Scene, root: bpy.types.Collection,
                      paths: Iterable[CollectionPath],
                      armature_name: str) -> Dict[CollectionPath, bpy.types.Collection]:
    """
    Recreate chains of collections inside the copy collection.

    Parameters
    ----------
    scene : bpy.types.Scene
        The scene the original collections are in.
    root : bpy.types.Collection
        The ``<armature>_fs`` collection, which stands for the empty chain.
    paths : iterable of tuple of bpy.types.Collection
        Chains below the shared top, from :func:`collection_paths`. They are
        made in the order the originals appear in the Outliner.
    armature_name : str
        The original armature's name, stored on each new collection.

    Returns
    -------
    dict of tuple to bpy.types.Collection
        Each chain and every chain leading to it, to its copy: named
        ``<original>_fs``, with the original's colour tag, always visible.
    """
    # Each collection's place in the Outliner, top to bottom
    order: Dict[bpy.types.Collection, int] = {}

    def number(parent: bpy.types.Collection) -> None:
        for child in parent.children:
            order.setdefault(child, len(order))
            number(child)

    number(scene.collection)
    copies: Dict[CollectionPath, bpy.types.Collection] = {(): root}
    for path in sorted(paths, key=lambda chain: [order[c] for c in chain]):
        for depth in range(1, len(path) + 1):
            chain = path[:depth]
            if chain in copies:
                continue
            original = chain[-1]
            copy = bpy.data.collections.new(original.name + SUFFIX)
            copy[PART_OF_KEY] = armature_name
            copy.color_tag = original.color_tag
            copies[chain[:-1]].children.link(copy)
            copies[chain] = copy
    return copies


def _remove_collection(collection: bpy.types.Collection, scene: bpy.types.Scene) -> None:
    """
    Delete a copy collection, its objects, its recreated collections, and data
    nothing else uses. A collection inside it that Prepare Copy did not make is
    kept: it moves to the scene's root collection when it has no other parent.
    """
    for child in list(collection.children):
        if child.get(PART_OF_KEY) is not None:
            _remove_collection(child, scene)
        else:
            collection.children.unlink(child)
            if child.users == 0:
                scene.collection.children.link(child)
    for obj in list(collection.objects):
        data = obj.data
        bpy.data.objects.remove(obj)
        if data is not None and data.users == 0:
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Armature):
                bpy.data.armatures.remove(data)
    bpy.data.collections.remove(collection)


def _new_collection(scene: bpy.types.Scene, armature_obj: bpy.types.Object) -> bpy.types.Collection:
    """Replace the armature's previous copy collection with a new, empty one."""
    # Found before any removal: removing one also removes the collections inside it
    previous = [c for c in bpy.data.collections if c.get(SOURCE_KEY) == armature_obj.name]
    for collection in previous:
        _remove_collection(collection, scene)
    collection = bpy.data.collections.new(armature_obj.name + SUFFIX)
    collection[SOURCE_KEY] = armature_obj.name
    scene.collection.children.link(collection)
    return collection


def _copy_armature(armature_obj: bpy.types.Object, matrix: Matrix,
                   collection: bpy.types.Collection) -> bpy.types.Object:
    """Copy the armature data, convert its bones by ``matrix @ matrix_world``."""
    data = armature_obj.data.copy()
    data.name = armature_obj.data.name + SUFFIX
    data.pose_position = 'POSE'
    data.transform(matrix @ armature_obj.matrix_world)
    copy = bpy.data.objects.new(armature_obj.name + SUFFIX, data)
    # Draw the bones over the meshes
    copy.show_in_front = True
    collection.objects.link(copy)
    return copy


def _copy_mesh(obj: bpy.types.Object, depsgraph, matrix: Matrix, flip_faces: bool,
               armature_copy: bpy.types.Object,
               collection: bpy.types.Collection) -> bpy.types.Object:
    """Copy one evaluated mesh into converted space; see :func:`prepare_copy`."""
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph),
                                           preserve_all_data_layers=True, depsgraph=depsgraph)
    mesh.name = obj.name + SUFFIX
    full = matrix @ obj.matrix_world
    normal_matrix = full.to_3x3().inverted().transposed()
    normals = [(normal_matrix @ corner.vector).normalized() for corner in mesh.corner_normals]
    mesh.transform(full, shape_keys=True)
    if flip_faces:
        order = flipped_corner_order((p.loop_start for p in mesh.polygons),
                                     (p.loop_total for p in mesh.polygons))
        mesh.flip_normals()
        normals = [normals[i] for i in order]
    # transform() inverts normals under a mirror and flip_normals() ignores
    # custom normals, so set the intended corner normals explicitly
    mesh.normals_split_custom_set(normals)
    mesh.materials.clear()
    for slot in obj.material_slots:
        mesh.materials.append(slot.material)
    copy = bpy.data.objects.new(obj.name + SUFFIX, mesh)
    collection.objects.link(copy)
    copy.parent = armature_copy
    modifier = copy.modifiers.new("Armature", 'ARMATURE')
    modifier.object = armature_copy
    return copy


def prepare_copy(context: bpy.types.Context, armature_obj: bpy.types.Object,
                 mirror_z: bool, flip_faces: bool) -> PreparedCopy:
    """
    Copy an armature and its meshes into the collection ``<armature>_fs``,
    converted into the space FbxImporter reads.

    Each mesh copy holds the original evaluated in the armature's rest pose,
    with its other modifiers applied, multiplied by the conversion matrix and
    the original's world matrix; normals follow the same matrix, so Mirror Z
    negates their Z and keeps each face's corner order. Copies have identity
    transforms and share the originals' materials. The armature copy is shown
    In Front. The collections holding the originals are recreated inside the
    copy collection below the ones they all share at the top (see
    :func:`shared_top`), and each copy is linked where its original is. A
    previous copy of the same armature is replaced. The originals, the
    selection and the active object are not changed.

    Parameters
    ----------
    context : bpy.types.Context
        Current Blender context.
    armature_obj : bpy.types.Object
        The armature to copy.
    mirror_z : bool
        Negate Z of positions and normals (FbxImporter's Mirror Z).
    flip_faces : bool
        Reverse each face's corner order (FbxImporter's Flip Faces).

    Returns
    -------
    PreparedCopy
        The collection, the armature copy and the mesh copies.
    """
    scene = context.scene
    matrix = conversion_matrix(mirror_z)
    meshes = armature_meshes(armature_obj, scene.objects)
    # Each original's chains of collections, below the ones they all share
    paths = {obj: collection_paths(scene, obj) for obj in [armature_obj] + meshes}
    top = len(shared_top(path for chains in paths.values() for path in chains))
    paths = {obj: [path[top:] for path in chains] or [()] for obj, chains in paths.items()}
    data = armature_obj.data
    saved_position = data.pose_position
    data.pose_position = 'REST'
    try:
        context.view_layer.update()
        depsgraph = context.evaluated_depsgraph_get()
        collection = _new_collection(scene, armature_obj)
        collection[MIRROR_Z_KEY] = mirror_z
        collection[FLIP_FACES_KEY] = flip_faces
        copies = _copy_collections(scene, collection,
                                   [path for chains in paths.values() for path in chains],
                                   armature_obj.name)
        armature_copy = _copy_armature(armature_obj, matrix, copies[paths[armature_obj][0]])
        for path in paths[armature_obj][1:]:
            copies[path].objects.link(armature_copy)
        result = PreparedCopy(collection, armature_copy)
        for obj in meshes:
            copy = _copy_mesh(obj, depsgraph, matrix, flip_faces, armature_copy,
                              copies[paths[obj][0]])
            for path in paths[obj][1:]:
                copies[path].objects.link(copy)
            result.meshes.append(copy)
    finally:
        data.pose_position = saved_position
        context.view_layer.update()
    return result
