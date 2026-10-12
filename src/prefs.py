# The Mirror Z and Flip Faces choices, kept as add-on preferences so Blender
# remembers them between sessions (when it saves its preferences)

from typing import Optional

import bpy
from bpy.props import BoolProperty


class FS_FBX_TOOLS_preferences(bpy.types.AddonPreferences):
    """Options of the FS FBX Tools add-on"""
    bl_idname = __package__

    mirror_z: BoolProperty(
        name="Mirror Z",
        description="Negate Z of positions and normals, as FbxImporter's Mirror Z does",
        default=False,
    )
    flip_faces: BoolProperty(
        name="Flip Faces",
        description="Reverse the order of each face's corners, as FbxImporter's Flip Faces does",
        default=False,
    )

    def draw(self, context):
        self.layout.prop(self, "mirror_z")
        self.layout.prop(self, "flip_faces")


def get(context: bpy.types.Context) -> Optional[FS_FBX_TOOLS_preferences]:
    """
    Find the add-on's preferences.

    Parameters
    ----------
    context : bpy.types.Context
        Current Blender context.

    Returns
    -------
    FS_FBX_TOOLS_preferences or None
        The preferences, or None when the add-on is not enabled.
    """
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon is not None else None
