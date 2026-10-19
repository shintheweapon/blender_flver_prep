# The Y-up views of the 3D Viewport: fixed rotations that show the prepared
# copies upright; no UI

from typing import Dict, Tuple

from mathutils import Matrix, Quaternion, Vector

Axes = Tuple[Vector, Vector, Vector]

# For each view: the world directions of the screen's right, the screen's up,
# and the direction towards the viewer. The name's axis is the side the
# viewer stands on, as Blender's own Front looks from -Y.
VIEWS: Dict[str, Axes] = {
    # From -Z towards +Z, Y up: Ctrl+Numpad 7 (Bottom) rolled 180 degrees
    'FRONT': (Vector((-1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, -1.0))),
    # From -X towards +X, Y up; relates to FRONT as Blender's Right to its Front
    'SIDE': (Vector((0.0, 0.0, 1.0)), Vector((0.0, 1.0, 0.0)), Vector((-1.0, 0.0, 0.0))),
    # From +Y down towards -Y, +Z up the screen; relates to FRONT as Blender's
    # Top to its Front
    'TOP': (Vector((-1.0, 0.0, 0.0)), Vector((0.0, 0.0, 1.0)), Vector((0.0, 1.0, 0.0))),
}


def view_rotation(side: str) -> Quaternion:
    """
    Rotation of a 3D Viewport that shows one of the Y-up views.

    Parameters
    ----------
    side : str
        A key of :data:`VIEWS`: 'FRONT', 'SIDE' or 'TOP'.

    Returns
    -------
    mathutils.Quaternion
        The value for ``RegionView3D.view_rotation``: its matrix's columns are
        the screen's right, the screen's up and the direction towards the
        viewer, in world space.

    Raises
    ------
    KeyError
        When ``side`` is not a key of :data:`VIEWS`.
    """
    right, up, towards_viewer = VIEWS[side]
    return Matrix((right, up, towards_viewer)).transposed().to_quaternion()
