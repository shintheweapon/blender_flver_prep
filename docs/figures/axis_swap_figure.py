"""
Fig. 3 of the paper docs/paper/ER_NORMAL_MAPS.md: the axis swap that carries a
Blender scene into FLVER space.

The figure has two parts:

- **animated, on top:** a character's coordinates go through the two steps of
  the swap, a -90 degree rotation about X and then Z negated, inside fixed axes
  drawn as Blender's Front view shows them (X right, Z up, Y into the scene),
  in the same slanted projection as Fig. 2. The frames are computed here and
  written as SMIL keyframes, since a rotation seen in perspective is not a 2D
  transform of the picture;
- **static, below:** the three stages, each seen from in front of the
  character.

``make_figures`` registers and writes it; the geometry comes from ``axes``,
the drawing parts from ``svg_parts``.
"""

import math

from axes import BLENDER_TO_FLVER, IDENTITY, NEGATE_Z, ROTATE_X_MINUS_90, apply, character_axes, multiply
from svg_parts import BLUE, GREEN, RED, fmt, into_screen, line, out_of_screen, project, signed, svg, text

AXIS_STAGES = (
    ("Blender", IDENTITY),
    ("Rotated −90° about X", ROTATE_X_MINUS_90),
    ("Then Z negated: FLVER", BLENDER_TO_FLVER),
)

# The animation: one loop, its frames and its stages as shares of the loop
LOOP_SECONDS = 30
FRAMES = 91
ROTATE = (0.17, 0.40)
NEGATE = (0.55, 0.75)
STEP_STARTS = (0.0, 0.17, 0.40, 0.55, 0.75)
STEPS = (
    ("Blender", ("Up +Z, forward −Y, left side +X.", "Right-handed.")),
    ("Rotate −90° about X", ("Up turns to +Y, forward to +Z.",)),
    ("After the rotation", ("Up +Y, forward +Z, left side +X.", "Still right-handed.")),
    ("Negate Z", ("Forward flips to −Z: a reflection,", "not a rotation.")),
    ("FLVER", ("Up +Y, forward −Z, left side +X.",)),
)
PANEL_HEIGHT = 330
ORIGIN = (400.0, 235.0)
AXIS_LENGTHS = {"X": 120.0, "Y": 190.0, "Z": 150.0}
BODY = "#888780"
FORWARD = "#EF9F27"
LEFT = "#7F77DD"

# The character in its own frame: (left side, up, forward) in drawing units
HUMANOID = {
    "head": (0.0, 96.0, 0.0), "neck": (0.0, 84.0, 0.0), "pelvis": (0.0, 40.0, 0.0),
    "left_foot": (12.0, 0.0, 0.0), "right_foot": (-12.0, 0.0, 0.0),
    "left_shoulder": (15.0, 78.0, 0.0), "right_shoulder": (-15.0, 78.0, 0.0),
    "left_hand": (34.0, 52.0, 0.0), "right_hand": (-34.0, 52.0, 0.0),
    "nose": (0.0, 96.0, 26.0),
}
# Segments: (from, to, colour, width)
SEGMENTS = (
    ("pelvis", "left_foot", BODY, 4.0), ("pelvis", "right_foot", BODY, 4.0), ("neck", "pelvis", BODY, 5.0),
    ("right_shoulder", "left_shoulder", BODY, 4.0), ("right_shoulder", "right_hand", BODY, 3.5),
    ("left_shoulder", "left_hand", LEFT, 3.5), ("head", "nose", FORWARD, 3.0),
)
# The character in Blender: left side +X, up +Z, forward -Y
BLENDER_LEFT, BLENDER_UP, BLENDER_FORWARD = (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)


def _ease(x):
    """Ease in and out: 0 to 1 with zero speed at both ends."""
    return 2 * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 2 / 2


def _progress(t, span):
    """How far through ``span`` (start, end) the loop time ``t`` is, eased, from 0 to 1."""
    start, end = span
    if t <= start:
        return 0.0
    if t >= end:
        return 1.0
    return _ease((t - start) / (end - start))


def stage_matrix(t):
    """
    The matrix the character's coordinates have gone through at loop time t.

    Parameters
    ----------
    t : float
        From 0 (Blender) to 1 (FLVER).

    Returns
    -------
    tuple of tuple of float
        A rotation about X by -90 degrees times the rotation's progress, then
        Z scaled from +1 to -1 by the negation's progress. It is the identity
        at 0, ``ROTATE_X_MINUS_90`` once the rotation is done and
        ``BLENDER_TO_FLVER`` at the end.
    """
    angle = -math.pi / 2 * _progress(t, ROTATE)
    c, s = math.cos(angle), math.sin(angle)
    rotation = ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))
    if _progress(t, ROTATE) == 1.0:
        rotation = ROTATE_X_MINUS_90
    scale = 1 - 2 * _progress(t, NEGATE)
    if _progress(t, NEGATE) == 1.0:
        return multiply(NEGATE_Z, rotation)
    return multiply(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, scale)), rotation)


def character_points(matrix):
    """
    The humanoid's points in Blender coordinates after a matrix.

    Returns
    -------
    dict
        Name to ``(x, y, z)``.
    """
    left, up, forward = (apply(matrix, v) for v in (BLENDER_LEFT, BLENDER_UP, BLENDER_FORWARD))
    return {name: tuple(a * left[i] + b * up[i] + c * forward[i] for i in range(3))
            for name, (a, b, c) in HUMANOID.items()}


def to_screen(point):
    """
    A point in Blender coordinates on screen: drawn at (X, Z, -Y), as Blender's
    Front view shows it, in Fig. 2's projection.

    Returns
    -------
    tuple of float
    """
    x, y, z = point
    return project(ORIGIN, (x, z, -y))


def frame_times():
    """The loop times of the keyframes, from 0 to 1."""
    return [i / (FRAMES - 1) for i in range(FRAMES)]


def _animate(attribute, values, times):
    return (f'<animate attributeName="{attribute}" values="{";".join(values)}" '
            f'keyTimes="{";".join(fmt_time(t) for t in times)}" dur="{LOOP_SECONDS}s" repeatCount="indefinite"/>')


def fmt_time(t):
    """A key time with up to four decimals."""
    return f"{t:.4f}".rstrip("0").rstrip(".") if t else "0"


def _head_points(a, b, size=8.0):
    """The arrowhead triangle at b for a segment from a to b, as SVG points."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    corners = (b, (b[0] - size * ux - size * 0.5 * uy, b[1] - size * uy + size * 0.5 * ux),
               (b[0] - size * ux + size * 0.5 * uy, b[1] - size * uy - size * 0.5 * ux))
    return " ".join(f"{fmt(x)},{fmt(y)}" for x, y in corners)


def animated_panel():
    """
    The animated panel: fixed axes, the moving humanoid and the step texts.

    Returns
    -------
    list of str
    """
    times = frame_times()
    frames = [{name: to_screen(p) for name, p in character_points(stage_matrix(t)).items()} for t in times]
    body = []
    for name, colour in (("X", RED), ("Y", GREEN), ("Z", BLUE)):
        end = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}[name]
        tip = to_screen(tuple(AXIS_LENGTHS[name] * c for c in end))
        body.append(line(ORIGIN[0], ORIGIN[1], tip[0], tip[1], colour, 2.0))
        dx, dy = tip[0] - ORIGIN[0], tip[1] - ORIGIN[1]
        norm = math.hypot(dx, dy)
        body.append(text(tip[0] + 14 * dx / norm, tip[1] + 14 * dy / norm + 4, name, "t", "middle"))
    for start, end, colour, width in SEGMENTS:
        first = frames[0]
        anims = "".join(_animate(attr, [fmt(f[point][axis]) for f in frames], times)
                        for attr, point, axis in (("x1", start, 0), ("y1", start, 1), ("x2", end, 0), ("y2", end, 1)))
        body.append(f'<line x1="{fmt(first[start][0])}" y1="{fmt(first[start][1])}" x2="{fmt(first[end][0])}" '
                    f'y2="{fmt(first[end][1])}" stroke="{colour}" stroke-width="{fmt(width)}" '
                    f'stroke-linecap="round">{anims}</line>')
    heads = [_head_points(f["head"], f["nose"]) for f in frames]
    body.append(f'<polygon points="{heads[0]}" fill="{FORWARD}">{_animate("points", heads, times)}</polygon>')
    for point, radius, colour in (("head", 11, BODY), ("left_hand", 5, LEFT)):
        anims = "".join(_animate(attr, [fmt(f[point][axis]) for f in frames], times)
                        for attr, axis in (("cx", 0), ("cy", 1)))
        body.append(f'<circle cx="{fmt(frames[0][point][0])}" cy="{fmt(frames[0][point][1])}" r="{radius}" '
                    f'fill="{colour}">{anims}</circle>')
    for index, (heading, lines) in enumerate(STEPS):
        start = STEP_STARTS[index]
        end = STEP_STARTS[index + 1] if index + 1 < len(STEPS) else None
        if index == 0:
            values, keys = ("1", "0"), (0.0, end)
        elif end is None:
            values, keys = ("0", "1"), (0.0, start)
        else:
            values, keys = ("0", "1", "0"), (0.0, start, end)
        anim = (f'<animate attributeName="opacity" values="{";".join(values)}" '
                f'keyTimes="{";".join(fmt_time(k) for k in keys)}" calcMode="discrete" dur="{LOOP_SECONDS}s" '
                f'repeatCount="indefinite"/>')
        parts = [text(20, 40, f"{index + 1}. {heading}", "t h")]
        parts += [text(20, 64 + 20 * i, content) for i, content in enumerate(lines)]
        body.append(f'<g opacity="{values[0]}">{anim}{"".join(parts)}</g>')
    return body


def static_panels():
    """
    The three stages, each seen from in front of the character.

    Returns
    -------
    list of str
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
        forward = axes["forward"]
        positive = "+" + forward[1]
        body += (out_of_screen if forward.startswith("+") else into_screen)(ox, oy)
        body.append(text(ox - 12, oy + 20, positive, "t", "end"))
        body.append(text(cx, 186, title, "t h", "middle"))
        body.append(text(cx, 206, f"{axes['handedness'].capitalize()}-handed", anchor="middle"))
        body.append(text(cx, 222, f"Forward {signed(forward)}, up {signed(axes['up'])}, left side "
                                  f"{signed(axes['left'])}", anchor="middle"))
    body += out_of_screen(60, 256)
    body.append(text(74, 260, "Out of the screen"))
    body += into_screen(220, 256)
    body.append(text(234, 260, "Into the screen"))
    body.append(text(380, 260, "Each panel: the character seen from in front."))
    return body


def figure_axis_swap():
    """
    Fig. 3: the animated panel above the three static panels.

    Returns
    -------
    str
    """
    body = animated_panel()
    body.append(f'<g transform="translate(0,{PANEL_HEIGHT})">')
    body += static_panels()
    body.append("</g>")
    return svg(680, PANEL_HEIGHT + 280, "The axis swap from Blender into FLVER space",
               "Top, animated over 30 seconds: fixed axes drawn as Blender's Front view shows them, X to the right, "
               "Z up and Y into the scene. A character stands facing the viewer, up +Z, forward -Y, left side +X. "
               "Its coordinates are rotated -90 degrees about X, which lays it on its back, up +Y and forward +Z; "
               "then Z is negated, a reflection, which turns it face down, forward -Z, with the left side still "
               "at +X. Below, three panels show the character's axes seen from in front, with its left side to the "
               "right of the screen. In Blender, X points right, Z up and Y into the screen: right-handed, with "
               "forward along -Y. After the rotation, Y points up and Z out of the screen: still right-handed, with "
               "forward along +Z. After Z is negated, Z points into the screen: left-handed, as in FLVER, with "
               "forward along -Z and the left side still along +X.", body)
