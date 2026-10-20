# The Y-up views of the 3D Viewport: fixed rotations that show the prepared
# copies upright, and the 90 degree roll; no UI

import math
from typing import Dict, Tuple

from mathutils import Matrix, Quaternion, Vector

Axes = Tuple[Vector, Vector, Vector]

# For each view: the world directions of the screen's right, the screen's up,
# and the direction towards the viewer. The key's axis is the side the viewer
# stands on, as Blender's own Front looks from -Y. Each opposite view is its
# partner turned half a turn, as Blender's are: about the screen's up for the
# Z and X sides (Ctrl+Numpad 1, Ctrl+Numpad 3), about the screen's right for
# the Y sides (Ctrl+Numpad 7).
VIEWS: Dict[str, Axes] = {
    # From -Z towards +Z, Y up: Ctrl+Numpad 7 (Bottom) rolled 180 degrees
    'NEG_Z': (Vector((-1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, -1.0))),
    'POS_Z': (Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0))),
    # From -X towards +X, Y up; relates to NEG_Z as Blender's Right to its Front
    'NEG_X': (Vector((0.0, 0.0, 1.0)), Vector((0.0, 1.0, 0.0)), Vector((-1.0, 0.0, 0.0))),
    'POS_X': (Vector((0.0, 0.0, -1.0)), Vector((0.0, 1.0, 0.0)), Vector((1.0, 0.0, 0.0))),
    # From +Y down towards -Y, +Z up the screen; relates to NEG_Z as Blender's
    # Top to its Front
    'POS_Y': (Vector((-1.0, 0.0, 0.0)), Vector((0.0, 0.0, 1.0)), Vector((0.0, 1.0, 0.0))),
    'NEG_Y': (Vector((-1.0, 0.0, 0.0)), Vector((0.0, 0.0, -1.0)), Vector((0.0, -1.0, 0.0))),
}

# The X sides with Side Up set to Z-Down: -Z up the screen. NEG_X here is
# NEG_X of VIEWS rolled 90 degrees clockwise on screen.
Z_DOWN_VIEWS: Dict[str, Axes] = {
    'NEG_X': (Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, -1.0)), Vector((-1.0, 0.0, 0.0))),
    'POS_X': (Vector((0.0, -1.0, 0.0)), Vector((0.0, 0.0, -1.0)), Vector((1.0, 0.0, 0.0))),
}


def view_rotation(side: str, side_up: str = 'Y_UP') -> Quaternion:
    """
    Rotation of a 3D Viewport that shows one of the Y-up views.

    Parameters
    ----------
    side : str
        A key of :data:`VIEWS`: 'NEG_Z', 'POS_Z', 'NEG_X', 'POS_X', 'POS_Y'
        or 'NEG_Y'.
    side_up : str, optional
        'Y_UP' (default) or 'Z_DOWN'. With 'Z_DOWN', the X sides come from
        :data:`Z_DOWN_VIEWS`; the other sides ignore it.

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
    axes = VIEWS[side]
    if side_up == 'Z_DOWN' and side in Z_DOWN_VIEWS:
        axes = Z_DOWN_VIEWS[side]
    right, up, towards_viewer = axes
    return Matrix((right, up, towards_viewer)).transposed().to_quaternion()


def rolled(rotation: Quaternion, direction: str) -> Quaternion:
    """
    Turn a view 90 degrees about its own viewing axis.

    Parameters
    ----------
    rotation : mathutils.Quaternion
        The view's rotation (``RegionView3D.view_rotation``).
    direction : str
        'RIGHT' turns the picture clockwise on screen, 'LEFT' anti-clockwise.

    Returns
    -------
    mathutils.Quaternion
        The rolled rotation.

    Raises
    ------
    ValueError
        When ``direction`` is neither 'LEFT' nor 'RIGHT'.
    """
    if direction not in ('LEFT', 'RIGHT'):
        raise ValueError(direction)
    angle = math.pi / 2 if direction == 'RIGHT' else -math.pi / 2
    return rotation @ Quaternion((0.0, 0.0, 1.0), angle)


def face_side(mirrored: bool) -> str:
    """
    The side the copy's face is on, for an original that faces -Y.

    Parameters
    ----------
    mirrored : bool
        Whether the copy was made with Mirror Z.

    Returns
    -------
    str
        'POS_Z' for a copy made without Mirror Z, 'NEG_Z' with it.
    """
    return 'NEG_Z' if mirrored else 'POS_Z'
