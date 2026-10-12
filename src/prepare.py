# Copies an armature and its meshes into a new collection, converted into the
# axes FbxImporter reads (raw mesh data, Y up, no object transforms); no UI

from dataclasses import dataclass, field
from typing import Iterable, List

import bpy
from bpy_extras.io_utils import axis_conversion
from mathutils import Matrix

# Suffix of every copied object, mesh, armature and of the collection
SUFFIX = "_fs"
# Custom property on the collection naming the armature it was made from
SOURCE_KEY = "fs_fbx_source"


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


def _remove_collection(collection: bpy.types.Collection) -> None:
    """Delete a collection, its objects, and their data when nothing else uses it."""
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
    for collection in list(bpy.data.collections):
        if collection.get(SOURCE_KEY) == armature_obj.name:
            _remove_collection(collection)
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
    transforms and share the originals' materials. A previous copy of the same
    armature is replaced. The originals, the selection and the active object
    are not changed.

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
    matrix = conversion_matrix(mirror_z)
    meshes = armature_meshes(armature_obj, context.scene.objects)
    data = armature_obj.data
    saved_position = data.pose_position
    data.pose_position = 'REST'
    try:
        context.view_layer.update()
        depsgraph = context.evaluated_depsgraph_get()
        collection = _new_collection(context.scene, armature_obj)
        armature_copy = _copy_armature(armature_obj, matrix, collection)
        result = PreparedCopy(collection, armature_copy)
        for obj in meshes:
            result.meshes.append(_copy_mesh(obj, depsgraph, matrix, flip_faces,
                                            armature_copy, collection))
    finally:
        data.pose_position = saved_position
        context.view_layer.update()
    return result
