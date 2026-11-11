"""
The check of docs/paper/ER_NORMAL_MAPS.md, Section IV-B: how a stored tangent
frame relates to its mesh.

At every corner of every triangle, the stored tangent ``(T, W)`` is compared
with the triangle's UV derivatives from ``tangent_geometry.uv_derivatives``:
the value of W, the length of T, how far T is from orthogonal to the normal,
how closely T follows +V, and whether W matches equation (9) of the paper.
Reading the mesh from a game file is left to the caller.
"""

import math

from tangent_geometry import cross, dot, uv_derivatives


class Corner:
    """
    The comparison at one triangle corner.

    Parameters
    ----------
    w : float
        The stored W.
    length : float
        The length of the stored T.
    normal_dot : float
        ``|T . N|`` with both scaled to unit length: 0 when T is orthogonal
        to N.
    v_cos : float or None
        The cosine between T and dp/dv with its component along N removed: 1
        when T lies along +V. None when that direction has no length.
    w_rule : bool
        True when the sign of W is ``-sign(N . (dp/du x dp/dv))``, equation
        (9).
    uv_sign : int
        The sign of the triangle's ``d``, +1 or -1: its UV orientation.
    """

    def __init__(self, w, length, normal_dot, v_cos, w_rule, uv_sign):
        self.w = w
        self.length = length
        self.normal_dot = normal_dot
        self.v_cos = v_cos
        self.w_rule = w_rule
        self.uv_sign = uv_sign


def _unit(a):
    length = math.sqrt(dot(a, a))
    return tuple(c / length for c in a) if length > 1e-12 else None


def frame_checks(positions, normals, uvs, triangles, tangents):
    """
    Compare each stored tangent with the mesh, at every triangle corner.

    Triangles with a repeated corner or no UV area (``uv_derivatives`` gives
    None) are skipped, as ``tangent_geometry.build_frame`` skips them. A
    corner whose tangent or normal has no length is skipped too.

    Parameters
    ----------
    positions, normals : sequence of tuple of float
        One 3D position and normal per vertex.
    uvs : sequence of tuple of float
        One ``(u, v)`` per vertex, as stored.
    triangles : sequence of tuple of int
        Three vertex indices per triangle.
    tangents : sequence of tuple of float
        One stored ``(x, y, z, w)`` tangent per vertex.

    Returns
    -------
    list of Corner
    """
    corners = []
    for a, b, c in triangles:
        if a == b or b == c or a == c:
            continue
        solved = uv_derivatives((positions[a], positions[b], positions[c]), (uvs[a], uvs[b], uvs[c]))
        if solved is None:
            continue
        d, dp_du, dp_dv = solved
        for i in (a, b, c):
            t, w = tuple(tangents[i][:3]), tangents[i][3]
            t_unit, n_unit = _unit(t), _unit(normals[i])
            if t_unit is None or n_unit is None:
                continue
            in_plane = tuple(p - n_unit[k] * dot(n_unit, dp_dv) for k, p in enumerate(dp_dv))
            v_unit = _unit(in_plane)
            rule = -1 if dot(n_unit, cross(dp_du, dp_dv)) > 0 else 1
            corners.append(Corner(w, math.sqrt(dot(t, t)), abs(dot(t_unit, n_unit)),
                                  None if v_unit is None else dot(t_unit, v_unit),
                                  (1 if w > 0 else -1) == rule, 1 if d > 0 else -1))
    return corners


def _share(corners):
    return sum(1 for corner in corners if corner.w_rule) / len(corners) if corners else None


def summarise(corners):
    """
    The values the paper's table gives for one part.

    Parameters
    ----------
    corners : sequence of Corner
        From ``frame_checks``.

    Returns
    -------
    dict
        ``w_values`` (sorted list), ``length`` (min, max), ``normal_dot_99``
        (the 99th percentile of ``normal_dot``), ``v_cos_median``,
        ``w_rule`` (the share of corners where it holds), and
        ``w_rule_by_uv_sign`` (that share for +1 and -1, None where a sign
        has no corners).

    Raises
    ------
    ValueError
        When there are no corners.
    """
    if not corners:
        raise ValueError("no corners to summarise")
    lengths = [corner.length for corner in corners]
    normal_dots = sorted(corner.normal_dot for corner in corners)
    v_cosines = sorted(corner.v_cos for corner in corners if corner.v_cos is not None)
    middle = len(v_cosines) // 2
    median = None
    if v_cosines:
        median = v_cosines[middle] if len(v_cosines) % 2 else (v_cosines[middle - 1] + v_cosines[middle]) / 2
    return {
        "w_values": sorted({corner.w for corner in corners}),
        "length": (min(lengths), max(lengths)),
        "normal_dot_99": normal_dots[min(len(normal_dots) - 1, int(0.99 * len(normal_dots)))],
        "v_cos_median": median,
        "w_rule": _share(corners),
        "w_rule_by_uv_sign": {sign: _share([c for c in corners if c.uv_sign == sign]) for sign in (1, -1)},
    }
