# Shared helpers that build small Blender scenes for tests

from math import radians
from typing import Dict, Iterable, Optional, Tuple

import bpy
from mathutils import Euler, Matrix, Vector

BoneSpec = Tuple[str, Optional[str], Tuple[float, float, float], Tuple[float, float, float]]


def new_scene() -> None:
    """Empty the current file so each test starts from a clean scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_armature(bones: Iterable[BoneSpec], name: str = 'Armature',
                  matrix: Matrix = Matrix.Identity(4)) -> bpy.types.Object:
    """
    Create an armature object from bone specifications.

    Parameters
    ----------
    bones : iterable of tuple
        ``(name, parent_name, head, tail)`` per bone, parents first.
    name : str
        Name for the armature object and data.
    matrix : mathutils.Matrix
        World matrix of the armature object.

    Returns
    -------
    bpy.types.Object
        The armature object, linked to the scene, active and in Object mode.
    """
    data = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = matrix
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones: Dict[str, bpy.types.EditBone] = {}
    for bone_name, parent_name, head, tail in bones:
        eb = data.edit_bones.new(bone_name)
        eb.head = head
        eb.tail = tail
        if parent_name is not None:
            eb.parent = edit_bones[parent_name]
        edit_bones[bone_name] = eb
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def make_skinned_mesh(name: str, armature_obj: bpy.types.Object, bone_name: str,
                      parented: bool = True,
                      matrix: Matrix = Matrix.Identity(4)) -> bpy.types.Object:
    """
    Create a closed mesh (an octahedron) weighted fully to one bone.

    Parameters
    ----------
    name : str
        Name for the mesh object and data.
    armature_obj : bpy.types.Object
        Armature for the Armature modifier (and parent when ``parented``).
    bone_name : str
        Vertex group name, holding every vertex at weight 1.
    parented : bool
        Parent the mesh to the armature; otherwise only the modifier links it.
    matrix : mathutils.Matrix
        World matrix of the mesh object.

    Returns
    -------
    bpy.types.Object
        The mesh object, linked to the scene.
    """
    verts = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1.5), (0, 0, -1)]
    faces = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4),
             (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    group = obj.vertex_groups.new(name=bone_name)
    group.add(list(range(len(verts))), 1.0, 'REPLACE')
    modifier = obj.modifiers.new('Armature', 'ARMATURE')
    modifier.object = armature_obj
    if parented:
        obj.parent = armature_obj
        obj.matrix_parent_inverse = armature_obj.matrix_world.inverted()
    obj.matrix_world = matrix
    return obj


def transform(location=(0.0, 0.0, 0.0), rotation_deg=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)) -> Matrix:
    """Build a world matrix from location, Euler XYZ rotation in degrees and scale."""
    rotation = Euler([radians(a) for a in rotation_deg], 'XYZ').to_matrix().to_4x4()
    return Matrix.Translation(Vector(location)) @ rotation @ Matrix.Diagonal(Vector(scale).to_4d())
