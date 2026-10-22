# Writes a prepared _fs collection to an FBX file as it is; no UI

from typing import Optional

import bpy

from . import prepare

# Blender FBX export settings that write the copies' data unchanged:
# Forward Y and Up Z make the axis matrix the identity, and without Apply
# Transform the vertices are written raw (FBX Units Scale keeps x100 out of it)
EXPORT_SETTINGS = dict(
    use_selection=True,
    object_types={'ARMATURE', 'MESH'},
    axis_forward='Y',
    axis_up='Z',
    bake_space_transform=False,
    apply_scale_options='FBX_SCALE_UNITS',
    use_mesh_modifiers=True,
    add_leaf_bones=False,
)


def prepared_collection(armature_obj: bpy.types.Object) -> Optional[bpy.types.Collection]:
    """
    Find the ``_fs`` collection made from an armature.

    Parameters
    ----------
    armature_obj : bpy.types.Object
        The original armature, or its ``_fs`` copy.

    Returns
    -------
    bpy.types.Collection or None
        The collection tagged with the original armature's name, or None when
        Prepare Copy has not been run for it.
    """
    for collection in bpy.data.collections:
        source = collection.get(prepare.SOURCE_KEY)
        if source is None:
            continue
        if source == armature_obj.name or armature_obj.name in collection.all_objects:
            return collection
    return None


def export_collection(context: bpy.types.Context, collection: bpy.types.Collection,
                      filepath: str) -> int:
    """
    Write a prepared collection's armature and meshes to an FBX file.

    The selection and active object are restored afterwards, also when the
    export fails.

    Parameters
    ----------
    context : bpy.types.Context
        Current Blender context.
    collection : bpy.types.Collection
        A collection made by Prepare Copy.
    filepath : str
        Path of the FBX file to write.

    Returns
    -------
    int
        Number of meshes written.

    Raises
    ------
    RuntimeError
        When Blender's FBX export fails.
    """
    view_layer = context.view_layer
    selected = [obj for obj in view_layer.objects if obj.select_get()]
    active = view_layer.objects.active
    try:
        for obj in selected:
            obj.select_set(False)
        for obj in collection.all_objects:
            obj.select_set(True)
        bpy.ops.export_scene.fbx(filepath=filepath, **EXPORT_SETTINGS)
    finally:
        for obj in collection.all_objects:
            obj.select_set(False)
        for obj in selected:
            obj.select_set(True)
        view_layer.objects.active = active
    return sum(1 for obj in collection.all_objects if obj.type == 'MESH')
