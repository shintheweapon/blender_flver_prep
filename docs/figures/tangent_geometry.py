"""
The rules the figures of docs/NORMAL_MAPS.md draw: the tangent frame, the
directions in which the game reads green and red, and the tilts it decodes.

Two coordinate systems are used:

- **UV directions** are pairs ``(u, v)``: +U runs right across the image and
  +V runs down it (row 0 is the top). On screen these are also the drawing's
  directions, with y running down.
- **Drawn 3D directions** are triples ``(x, y, z)`` for the perspective views:
  a sheet lies flat on a table, +x to the right, +y up (the normal N) and +z
  towards the viewer. On an unmirrored island +U is +x and +V is +z, so the
  image's row 0 is the sheet's far edge.

FLVER space is left-handed. Shown in a right-handed drawing such as these,
its cross product points the opposite way to the right-hand rule: it follows
the left-hand rule (see ``cross_as_drawn``).
"""

import math

U = (1.0, 0.0)
V = (0.0, 1.0)


def cross(a, b):
    """
    Cross product by the usual formula.

    Parameters
    ----------
    a, b : tuple of float
        3D vectors.

    Returns
    -------
    tuple of float
        ``a x b``.
    """
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def cross_as_drawn(a, b):
    """
    The cross product of FLVER's left-handed space, for vectors given in the
    right-handed drawing frame: the opposite of ``cross``.

    Parameters
    ----------
    a, b : tuple of float
        3D vectors in the drawing frame.

    Returns
    -------
    tuple of float
        ``a x b`` as it appears in game (the left-hand rule).
    """
    return tuple(-c for c in cross(a, b))


def dot(a, b):
    """
    Dot product of two vectors of the same length.

    Returns
    -------
    float
    """
    return sum(x * y for x, y in zip(a, b))


def to_3d(uv, mirrored):
    """
    The drawn 3D direction of a UV direction on a flat island.

    Parameters
    ----------
    uv : tuple of float
        ``(u, v)`` direction.
    mirrored : bool
        True when the island's +U runs to the left (-x).

    Returns
    -------
    tuple of float
        ``(x, y, z)``.
    """
    return ((-uv[0] if mirrored else uv[0]), 0.0, uv[1])


def to_uv(xyz, mirrored):
    """
    The UV direction of a drawn 3D direction lying in a flat island.

    Returns
    -------
    tuple of float
        ``(u, v)``.
    """
    return ((-xyz[0] if mirrored else xyz[0]), xyz[2])


NORMAL = (0.0, 1.0, 0.0)


def vanilla_sign(mirrored):
    """
    The W the game stores on a vanilla island: the sign that makes W(N x T)
    point along +U, with T along +V.

    Parameters
    ----------
    mirrored : bool
        True for a mirrored island.

    Returns
    -------
    int
        -1 or +1.
    """
    n_x_t = cross_as_drawn(NORMAL, to_3d(V, mirrored))
    return 1 if dot(n_x_t, to_3d(U, mirrored)) > 0 else -1


class Case:
    """
    One way the tangents reach the game, as measured on imports.

    Parameters
    ----------
    key : str
        Short name used by the tests.
    tangent : tuple of float
        UV direction of the stored tangent T.
    sign : int
        W stored on an island that is unmirrored before any Transform.
    mirrored : bool
        True when the import mirrors the mesh, which reverses N x T
        relative to the UVs.
    """

    def __init__(self, key, tangent, sign, mirrored):
        self.key = key
        self.tangent = tangent
        self.sign = sign
        self.mirrored = mirrored


CASES = (
    Case("vanilla", V, -1, False),
    Case("none", U, -1, False),
    Case("mirror_z", U, -1, True),
)


def read_directions(case):
    """
    The UV directions along which the game reads green and red.

    The game reads green along T and red along W(N x T).

    Parameters
    ----------
    case : Case

    Returns
    -------
    tuple
        ``(green, red)``, each a ``(u, v)`` direction.
    """
    n_x_t = to_uv(cross_as_drawn(NORMAL, to_3d(case.tangent, False)), False)
    if case.mirrored:
        n_x_t = (-n_x_t[0], -n_x_t[1])
    red = (case.sign * n_x_t[0], case.sign * n_x_t[1])
    return case.tangent, red


def decode(tilt, case):
    """
    The tilt the game rebuilds from an authored tilt.

    The map stores the tilt's +U part in red and its +V part in green; the
    game puts red back along its red direction and green along its green
    direction.

    Parameters
    ----------
    tilt : tuple of float
        Authored ``(a, b)``: the +U and +V parts.
    case : Case

    Returns
    -------
    tuple of float
        The decoded ``(u, v)`` tilt.
    """
    green, red = read_directions(case)
    a, b = tilt
    return (a * red[0] + b * green[0], a * red[1] + b * green[1])


def dome_points(count=8):
    """
    Directions from the centre of a dome to points around it.

    Returns
    -------
    list of tuple
        ``count`` unit ``(u, v)`` directions, starting along +U and turning
        towards +V.
    """
    return [(round(math.cos(2 * math.pi * i / count), 6), round(math.sin(2 * math.pi * i / count), 6))
            for i in range(count)]


SPIN = "spin"
FLIP = "flip"

MOTION = {"vanilla": None, "none": SPIN, "mirror_z": FLIP}


def apply_motion(motion, direction):
    """
    Where a drawn direction ends after a panel's animation.

    On screen +U is right and +V is down, so a UV direction is also a screen
    direction. ``rotate(-90deg)`` takes (x, y) to (y, -x); the diagonal flip
    takes (x, y) to (y, x).

    Parameters
    ----------
    motion : str or None
        ``SPIN``, ``FLIP`` or None.
    direction : tuple of float

    Returns
    -------
    tuple of float
    """
    x, y = direction
    if motion == SPIN:
        return (y, -x)
    if motion == FLIP:
        return (y, x)
    return (x, y)
