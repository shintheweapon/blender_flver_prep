# Removing a mesh's vertex colors (its Color Attributes); no UI

from typing import List, Tuple

import bpy


def remove_color_attributes(mesh: bpy.types.Mesh, keep_render: bool) -> Tuple[List[str], List[str]]:
    """
    Remove the Color Attributes of a mesh.

    Every color attribute goes, whatever its domain (point or face corner)
    and type (byte or float), apart from the render color when it is kept.

    Parameters
    ----------
    mesh : bpy.types.Mesh
        The mesh data; it must not be in Edit Mode.
    keep_render : bool
        Keep the render color: the one the camera icon in the Color Attributes
        list marks, named by ``color_attributes.default_color_name``.

    Returns
    -------
    tuple of (list of str, list of str)
        The names removed, and the names kept (the render color, or nothing).
    """
    attributes = mesh.color_attributes
    render = attributes.default_color_name if keep_render else ""
    kept = [a.name for a in attributes if a.name == render]
    removed = [a.name for a in attributes if a.name != render]
    for name in removed:
        attributes.remove(attributes[name])
    return removed, kept
