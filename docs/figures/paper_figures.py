"""
The figures drawn only for the paper docs/paper/ER_NORMAL_MAPS.md: the axis
swap from Blender into FLVER space, the layout test on vanilla maps, one
triangle's UV derivatives and tangent frame, and the channel changes.

``make_figures`` registers and writes them; the geometry comes from ``axes``
and ``tangent_geometry``, the drawing parts from ``svg_parts``.
"""

from axes import BLENDER_TO_FLVER, FLVER_BELOW_VIEW, IDENTITY, ROTATE_X_MINUS_90, character_axes, on_screen
from svg_parts import BLUE, GREEN, RED, into_screen, legend, line, out_of_screen, svg, text
from tangent_geometry import (CASES, build_frame, cross, decode, decode_colour, dome_points, dot, encode_colour,
                              uv_derivatives, workaround)

# The worked example of the paper's Section VI
EXAMPLE_POSITIONS = ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 0.0, 1.0))
EXAMPLE_UVS = ((0.0, 0.0), (0.5, 0.0), (0.0, 0.25))
EXAMPLE_NORMAL = (0.0, -1.0, 0.0)

AXIS_STAGES = (
    ("Blender", IDENTITY),
    ("Rotated −90° about X", ROTATE_X_MINUS_90),
    ("Then Z negated: FLVER", BLENDER_TO_FLVER),
)


def signed(name):
    """An axis name with a typographic minus sign."""
    return name.replace("-", "−")


def vector(v):
    """A vector as the paper writes it: whole numbers without a decimal point."""
    return "(" + ", ".join(signed(f"{c:g}") for c in (0.0 if abs(c) < 1e-12 else c for c in v)) + ")"


def figure_axis_swap():
    """
    The character's axes in Blender, after the rotation about X, and in FLVER
    space, each seen from in front.

    Returns
    -------
    str
    """
    body = []
    for index, (title, matrix) in enumerate(AXIS_STAGES):
        axes = character_axes(matrix)
        cx = 120 + 220 * index
        ox, oy = cx - 30, 130
        body.append(line(ox + 9, oy, ox + 80, oy, None, 2.0))
        body.append(text(ox + 86, oy + 4, signed(axes["left"]), "t"))
        body.append(line(ox, oy - 9, ox, oy - 80, None, 2.0))
        body.append(text(ox, oy - 88, signed(axes["up"]), "t", "middle"))
        front = axes["front"]
        positive = "+" + front[1]
        body += (out_of_screen if front.startswith("+") else into_screen)(ox, oy)
        body.append(text(ox - 12, oy + 20, positive, "t", "end"))
        body.append(text(cx, 186, title, "t h", "middle"))
        body.append(text(cx, 206, f"{axes['handedness'].capitalize()}-handed", anchor="middle"))
        body.append(text(cx, 222, f"Front {signed(front)}, up {signed(axes['up'])}, left side "
                                  f"{signed(axes['left'])}", anchor="middle"))
    body += out_of_screen(60, 256)
    body.append(text(74, 260, "Out of the screen"))
    body += into_screen(220, 256)
    body.append(text(234, 260, "Into the screen"))
    body.append(text(380, 260, "Each panel: the character seen from in front."))
    return svg(680, 280, "The axis swap from Blender into FLVER space",
               "Three panels show a character's axes seen from in front, with its left side to the right of the "
               "screen. In Blender, X points right, Z up and Y into the screen: right-handed, with the front "
               "along -Y. After a -90 degree rotation about X, Y points up and Z out of the screen: still "
               "right-handed, with the front along +Z. After Z is negated, Z points into the screen: "
               "left-handed, as in FLVER, with the front along -Z and the left side still along +X.", body)


def example_frame():
    """
    The worked example's partial derivatives and frame.

    Returns
    -------
    dict
        ``dp_du``, ``dp_dv``, ``T``, ``N x T``, ``B`` and ``N`` as FLVER
        vectors, and ``W``.
    """
    _, dp_du, dp_dv = uv_derivatives(EXAMPLE_POSITIONS, EXAMPLE_UVS)
    [(t, w)] = build_frame(EXAMPLE_POSITIONS, [EXAMPLE_NORMAL] * 3, EXAMPLE_UVS, [(0, 1, 2)],
                           [(0.0, 0.0, 0.0, 1.0)] * 3)[:1]
    n_x_t = cross(EXAMPLE_NORMAL, t)
    return {"dp_du": dp_du, "dp_dv": dp_dv, "T": t, "N x T": n_x_t, "B": tuple(w * c for c in n_x_t),
            "N": EXAMPLE_NORMAL, "W": w}


def drawn(v):
    """
    A FLVER vector as drawn in the view from below: ``(right, down)`` on
    screen, and its component out of the screen.

    Returns
    -------
    tuple of float
        ``(right, down, out)``.
    """
    right, up, out = on_screen(FLVER_BELOW_VIEW, v)
    return right, -up, out


def figure_uv_triangle():
    """
    The worked example's triangle in UV space and in game, with its partial
    derivatives and tangent frame.

    Returns
    -------
    str
    """
    frame = example_frame()
    body = []
    # UV space: U right, V down, 400 px per unit
    ox, oy = 110, 70
    uv = [(ox + 400 * u, oy + 400 * v) for u, v in EXAMPLE_UVS]
    points = " ".join(f"{x:g},{y:g}" for x, y in uv)
    body.append(f'<polygon class="p" points="{points}" stroke-width="1"/>')
    for (x, y), name, dx, dy, anchor in zip(uv, ("p₀", "p₁", "p₂"), (-6, 6, -6), (-6, -6, 14), ("end", "start", "end")):
        body.append(text(x + dx, y + dy, name, "t", anchor))
    body.append(text((uv[0][0] + uv[1][0]) / 2, oy - 8, "Δu₁ = 0.5", anchor="middle"))
    body.append(text(ox - 8, (uv[0][1] + uv[2][1]) / 2 + 4, "Δv₂ = 0.25", anchor="end"))
    body.append(line(ox + 120, oy + 120, ox + 170, oy + 120, None, 1.0))
    body.append(text(ox + 176, oy + 124, "+U"))
    body.append(line(ox + 120, oy + 120, ox + 120, oy + 160, None, 1.0))
    body.append(text(ox + 120, oy + 176, "+V", anchor="middle"))
    body.append(text(210, 276, "UV space", "t h", "middle"))
    body.append(text(210, 294, "U right, V down", anchor="middle"))
    # In game, seen from below: 100 px per unit
    gx, gy = 420, 70
    corners = []
    for p in EXAMPLE_POSITIONS:
        right, down, _ = drawn(p)
        corners.append((gx + 100 * right, gy + 100 * down))
    points = " ".join(f"{x:g},{y:g}" for x, y in corners)
    body.append(f'<polygon class="p" points="{points}" stroke-width="1"/>')
    for (x, y), name, dx, dy, anchor in zip(corners, ("p₀", "p₁", "p₂"), (-6, 6, -6), (-6, -6, 14),
                                            ("end", "start", "end")):
        body.append(text(x + dx, y + dy, name, "t", anchor))
    body.append(text((corners[0][0] + corners[1][0]) / 2, gy - 8, "e₁, along ∂p/∂u", anchor="middle"))
    body.append(text(gx - 8, (corners[0][1] + corners[2][1]) / 2 + 4, "e₂, along ∂p/∂v", anchor="end"))
    cx, cy = gx + 60, gy + 30
    for key, colour, length, dashed in (("T", GREEN, 44, False), ("B", RED, 44, False), ("N x T", RED, 36, True)):
        right, down, _ = drawn(frame[key])
        body.append(line(cx, cy, cx + length * right, cy + length * down, colour, 1.0 if dashed else 2.0,
                         dashed=dashed, head=not dashed))
    body += out_of_screen(cx, cy, 6.0)
    body.append(text(cx + 10, cy - 8, "N"))
    body.append(text(520, 276, "In game, seen from below", "t h", "middle"))
    body.append(text(520, 294, "x right, −z up, N out of the screen", anchor="middle"))
    body.append(text(520, 310, f"∂p/∂u = {vector(frame['dp_du'])}, ∂p/∂v = {vector(frame['dp_dv'])}",
                     anchor="middle"))
    body += legend(40, 342, GREEN, "T, along +V")
    body += legend(180, 342, RED, "B = W(N × T), along +U")
    body.append(line(390, 342, 414, 342, RED, 1.0, dashed=True, head=False))
    body.append(text(420, 346, f"N × T (left-hand rule), W = {signed(str(frame['W']))}"))
    return svg(680, 366, "One triangle in UV space and in game",
               "The worked example's triangle twice. Left, in UV space with U to the right and V down: p0 at "
               "the corner, p1 0.5 to the right, p2 0.25 down. Right, in game seen from below, with x to the "
               "right, -z up and the normal N out of the screen: the edge e1 along the partial derivative "
               "along U, e2 along the partial derivative along V, the tangent T pointing down along +V, N x T "
               "pointing left by the left-hand rule, and B = W(N x T) with W = -1 pointing right, along +U, as "
               "in the UV panel.", body)


# The tangent-space normals around a raised dome, as in Fig. 6, with this (x, y) length
DOME_TILT = 0.6

CHANNEL_CHANGES = (
    ("none", "Without a mirror", "rotated by 90°", "After (20)"),
    ("mirror_z", "With Z mirrored", "reflected about U = V", "After (21)"),
)


def channel_change_points(key):
    """
    The decoded tangent-space normals around a raised dome, from the map as
    authored and from the map after the channel change.

    Each authored normal is stored with ``encode_colour``; the changed map
    applies ``workaround``; the game decodes each map with
    ``decode_colour`` and ``decode`` through tangents along +U.

    Parameters
    ----------
    key : str
        ``"none"`` (without a mirror) or ``"mirror_z"`` (with Z mirrored).

    Returns
    -------
    list of tuple
        ``(direction, authored, changed)`` per dome point: the outward unit
        direction and the two decoded ``(u, v)`` components.
    """
    case = next(c for c in CASES if c.key == key)
    points = []
    for direction in dome_points():
        red, green = encode_colour(DOME_TILT * direction[0], DOME_TILT * direction[1])
        authored = decode(decode_colour(red, green)[:2], case)
        changed = decode(decode_colour(*workaround(red, green, key))[:2], case)
        points.append((direction, authored, changed))
    return points


def dome(cx, cy, decoded_points):
    """
    A dome's outline and its decoded normals, coloured by whether each
    points outward (raised), inward (dented) or sideways.

    Parameters
    ----------
    cx, cy : float
        The dome's centre.
    decoded_points : list of tuple
        ``(direction, decoded)`` per dome point.

    Returns
    -------
    list of str
    """
    body = [f'<circle cx="{cx}" cy="{cy}" r="40" fill="none" class="o" stroke-width="0.5" stroke-dasharray="3 3"/>']
    for direction, decoded in decoded_points:
        along = dot(decoded, direction) / DOME_TILT
        colour = RED if along > 0.99 else BLUE if along < -1e-6 else None
        px, py = cx + 40 * direction[0], cy + 40 * direction[1]
        scale = 30 / DOME_TILT
        body.append(line(px, py, px + scale * decoded[0], py + scale * decoded[1], colour, 1.5))
    return body


def figure_channel_changes():
    """
    The decoded normals around a raised dome through tangents along +U, from
    the map as authored and from the map after the channel change.

    Returns
    -------
    str
    """
    body = []
    for column, (key, title, authored_note, changed_note) in enumerate(CHANNEL_CHANGES):
        cx = 190 + 300 * column
        body.append(text(cx, 30, title, "t h", "middle"))
        points = channel_change_points(key)
        body += dome(cx, 110, [(d, a) for d, a, _ in points])
        body.append(text(cx, 184, f"Map as authored: {authored_note}", anchor="middle"))
        body += dome(cx, 270, [(d, c) for d, _, c in points])
        body.append(text(cx, 344, f"{changed_note}: outward, as authored", anchor="middle"))
    body += legend(60, 380, RED, "Outward (raised)", head=True)
    body += legend(240, 380, BLUE, "Inward (dented)", head=True)
    body += legend(420, 380, None, "Sideways", head=True)
    body.append(text(340, 408, "Derived from the measured frames; not tested in game.", anchor="middle"))
    return svg(680, 424, "Matching the map to tangents along +U",
               "Two columns, without a mirror and with Z mirrored, each with two domes seen from above. Top: "
               "the map as authored, read through tangents along +U: without a mirror every normal is rotated "
               "by 90 degrees and points sideways; with Z mirrored every normal is reflected about the line "
               "U = V, so the normals on that diagonal point outward and those on the other diagonal inward. "
               "Bottom: the map after the channel change, (20) or (21): every normal points outward, as "
               "authored. The changes are derived from the measured frames, not tested in game.", body)
