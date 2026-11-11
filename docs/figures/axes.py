"""
Coordinate systems and views for the paper docs/paper/ER_NORMAL_MAPS.md: the
axis swap that carries a Blender scene into FLVER space (Section III-C), and
the handedness of a coordinate system as seen on screen (Section II-C).

A view is given by three directions in a system's coordinates: to the right of
the screen, up, and out of the screen towards the viewer.
"""

from tangent_geometry import cross, dot

# The axis swap that carries a Blender scene into FLVER space (paper Section III-C), as 3x3 matrices acting on
# column vectors: a -90 degree rotation about X, then Z negated.
ROTATE_X_MINUS_90 = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0))
NEGATE_Z = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, -1.0))
IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

# A character in Blender: its left side, up and front directions.
CHARACTER = {"left": (1.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "front": (0.0, -1.0, 0.0)}


def apply(matrix, v):
    """
    A matrix times a column vector.

    Parameters
    ----------
    matrix : tuple of tuple of float
        Three rows.
    v : tuple of float

    Returns
    -------
    tuple of float
    """
    return tuple(dot(row, v) for row in matrix)


def multiply(a, b):
    """
    The matrix product ``a b``: apply ``b`` first, then ``a``.

    Returns
    -------
    tuple of tuple of float
    """
    columns = list(zip(*b))
    return tuple(tuple(dot(row, column) for column in columns) for row in a)


def determinant(m):
    """
    The determinant of a 3x3 matrix: -1 for a reflection, +1 for a rotation.

    Returns
    -------
    float
    """
    return dot(m[0], cross(m[1], m[2]))


BLENDER_TO_FLVER = multiply(NEGATE_Z, ROTATE_X_MINUS_90)


def screen_handedness(right, up, out):
    """
    The handedness of a coordinate system as seen in a view.

    With x to the right and y up, a system is right-handed when z points out
    of the screen and left-handed when z points into it. In general the sign
    of the determinant of the three screen directions, written in the
    system's coordinates, decides.

    Parameters
    ----------
    right, up, out : tuple of float
        The directions to the right, up and out of the screen, in the
        system's coordinates.

    Returns
    -------
    str
        ``"right"`` or ``"left"``.
    """
    return "right" if determinant((right, up, out)) > 0 else "left"


def axis_name(v):
    """
    The signed axis a coordinate direction lies along.

    Parameters
    ----------
    v : tuple of float
        A direction along one axis, such as ``(0, 0, -1)``.

    Returns
    -------
    str
        For example ``"-Z"``.

    Raises
    ------
    ValueError
        When the direction does not lie along exactly one axis.
    """
    along = [i for i, c in enumerate(v) if abs(c) > 1e-9]
    if len(along) != 1:
        raise ValueError(f"{v!r} does not lie along one axis")
    i = along[0]
    return ("+" if v[i] > 0 else "-") + "XYZ"[i]


def character_axes(matrix):
    """
    The axes along the character's left side, up and front after a matrix.

    Seen from in front, the character's left side is to the right of the
    screen, its up is up and its front points out of the screen.

    Parameters
    ----------
    matrix : tuple of tuple of float
        Applied to the Blender scene.

    Returns
    -------
    dict
        ``left``, ``up`` and ``front``: signed axis names, and ``handedness``
        as seen from in front.
    """
    moved = {key: apply(matrix, v) for key, v in CHARACTER.items()}
    axes = {key: axis_name(v) for key, v in moved.items()}
    axes["handedness"] = screen_handedness(moved["left"], moved["up"], moved["front"])
    return axes


# Views as (right, up, out of the screen), in each system's own coordinates.
BLENDER_FRONT_VIEW = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0))
FLVER_FRONT_VIEW = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, -1.0))
# FLVER space seen from below: x to the right, -z up, and -y (the worked example's normal) out of the screen
FLVER_BELOW_VIEW = ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, -1.0, 0.0))


def on_screen(view, v):
    """
    A vector's components along a view's screen directions.

    Parameters
    ----------
    view : tuple of tuple of float
        ``(right, up, out)``.
    v : tuple of float

    Returns
    -------
    tuple of float
        ``(right, up, out)`` components.
    """
    return tuple(dot(direction, v) for direction in view)
