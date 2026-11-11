"""
The rules the figures of docs/NORMAL_MAPS.md draw: the tangent frame, the
directions in which the game reads green and red, and the tilts it decodes.
It also holds the formulas of the paper docs/paper/ER_NORMAL_MAPS.md: the
colour encoding, the per-triangle UV directions, the tangents in the game's
convention, and the channel workarounds.

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


def decode_colour(red, green):
    """
    The tilt a normal-map pixel stores, from its red and green values.

    Parameters
    ----------
    red, green : float
        Channel values from 0 to 1.

    Returns
    -------
    tuple of float
        ``(x, y, z)``: ``x = 2R - 1``, ``y = 2G - 1``, and ``z`` rebuilt so the
        tilt has length 1 (0 when x and y already reach length 1).
    """
    x = 2.0 * red - 1.0
    y = 2.0 * green - 1.0
    return (x, y, math.sqrt(max(0.0, 1.0 - x * x - y * y)))


def encode_colour(x, y):
    """
    The red and green values that store a tilt: the inverse of ``decode_colour``.

    Parameters
    ----------
    x, y : float
        The tilt's +U and +V parts, from -1 to 1.

    Returns
    -------
    tuple of float
        ``(R, G)``.
    """
    return ((x + 1.0) / 2.0, (y + 1.0) / 2.0)


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _scale(a, s):
    return tuple(x * s for x in a)


def _length_squared(a):
    return dot(a, a)


def uv_derivatives(positions, uvs):
    """
    The directions along which U and V increase across one triangle.

    Solves ``e1 = du1 dp/du + dv1 dp/dv`` and ``e2 = du2 dp/du + dv2 dp/dv``
    for the two directions, as FbxImporter's ``TangentBuilder.Build`` does.

    Parameters
    ----------
    positions : sequence of tuple of float
        The three corners ``p0, p1, p2``.
    uvs : sequence of tuple of float
        Their ``(u, v)`` values, as stored in the FLVER.

    Returns
    -------
    tuple or None
        ``(d, dp_du, dp_dv)``, where ``d = du1 dv2 - du2 dv1``; None when the
        triangle has no UV area (``|d| < 1e-12``).
    """
    e1, e2 = _sub(positions[1], positions[0]), _sub(positions[2], positions[0])
    (du1, dv1), (du2, dv2) = _sub(uvs[1], uvs[0]), _sub(uvs[2], uvs[0])
    d = du1 * dv2 - du2 * dv1
    if abs(d) < 1e-12:
        return None
    dp_du = _scale(_sub(_scale(e1, dv2), _scale(e2, dv1)), 1.0 / d)
    dp_dv = _scale(_sub(_scale(e2, du1), _scale(e1, du2)), 1.0 / d)
    return d, dp_du, dp_dv


def build_frame(positions, normals, uvs, triangles, fallback):
    """
    Tangents in the game's convention, step by step as ``TangentBuilder.Build``
    builds them: T along +V and W so that W(N x T) points along +U.

    Each triangle adds its +U and +V directions, at length ``|e1 x e2|``, to
    its three corners; triangles with a repeated corner, no UV area or no
    size are skipped. Each vertex's +V sum, less its part along the normal,
    is its tangent, and W comes from the +U sum. A vertex without a usable
    normal or +V sum keeps its fallback tangent, with W made +1 or -1.

    Parameters
    ----------
    positions, normals : sequence of tuple of float
        One 3D position and normal per vertex.
    uvs : sequence of tuple of float
        One ``(u, v)`` per vertex.
    triangles : sequence of tuple of int
        Three vertex indices per triangle.
    fallback : sequence of tuple of float
        One ``(x, y, z, w)`` tangent per vertex.

    Returns
    -------
    list of tuple
        One ``(T, W)`` per vertex.
    """
    count = len(positions)
    u_sum = [(0.0, 0.0, 0.0)] * count
    v_sum = [(0.0, 0.0, 0.0)] * count
    for a, b, c in triangles:
        if a == b or b == c or a == c:
            continue
        corners = (positions[a], positions[b], positions[c])
        solved = uv_derivatives(corners, (uvs[a], uvs[b], uvs[c]))
        size = math.sqrt(_length_squared(cross(_sub(corners[1], corners[0]), _sub(corners[2], corners[0]))))
        if solved is None or size < 1e-20:
            continue
        _, dp_du, dp_dv = solved
        if _length_squared(dp_du) < 1e-24 or _length_squared(dp_dv) < 1e-24:
            continue
        u_vote = _scale(dp_du, size / math.sqrt(_length_squared(dp_du)))
        v_vote = _scale(dp_dv, size / math.sqrt(_length_squared(dp_dv)))
        for i in (a, b, c):
            u_sum[i] = _add(u_sum[i], u_vote)
            v_sum[i] = _add(v_sum[i], v_vote)

    frames = []
    for i in range(count):
        n = normals[i]
        n = _scale(n, 1.0 / math.sqrt(_length_squared(n))) if _length_squared(n) > 0 else (0.0, 0.0, 0.0)
        t = _sub(v_sum[i], _scale(n, dot(n, v_sum[i])))
        if (_length_squared(n) == 0 or _length_squared(v_sum[i]) == 0
                or _length_squared(t) <= 1e-8 * _length_squared(v_sum[i])):
            frames.append((tuple(fallback[i][:3]), -1 if fallback[i][3] < 0 else 1))
            continue
        t = _scale(t, 1.0 / math.sqrt(_length_squared(t)))
        frames.append((t, 1 if dot(cross(n, t), u_sum[i]) >= 0 else -1))
    return frames


WORKAROUND_SETTINGS = ("none", "mirror_z")


def workaround(red, green, setting):
    """
    The red and green values that make a map read as authored through
    tangents along +U, without ER Tangents.

    Transform None reads a stored tilt (a', b') as (b', -a'), so the map
    stores (-b, a); Transform Mirror Z reads it as (b', a'), so the map
    stores (b, a).

    Parameters
    ----------
    red, green : float
        The authored channel values, from 0 to 1.
    setting : str
        ``"none"`` (Transform None, Mirror unticked) or ``"mirror_z"``
        (Transform Mirror Z, Mirror ticked).

    Returns
    -------
    tuple of float
        The new ``(R, G)``.

    Raises
    ------
    ValueError
        For any other setting.
    """
    if setting == "none":
        return (1.0 - green, red)
    if setting == "mirror_z":
        return (green, red)
    raise ValueError(f"unknown setting {setting!r}; expected one of {WORKAROUND_SETTINGS}")


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
