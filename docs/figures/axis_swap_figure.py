"""
Fig. 3 of the paper docs/paper/ER_NORMAL_MAPS.md: the axis swap that carries a
Blender scene into FLVER space.

The figure has two parts, each its own SVG under one caption:

- **(a), animated** (``paper_axis_swap_animated.svg``): a character's coordinates go through the two steps of
  the swap, a -90 degree rotation about X and then Z negated, inside fixed axes
  drawn as Blender's Front view shows them (X right, Z up, Y into the scene),
  in the same slanted projection as Fig. 2. The frames are computed here and
  written as SMIL keyframes, since a rotation seen in perspective is not a 2D
  transform of the picture;
- **(b), static** (``paper_axis_swap.svg``): the three stages, each seen from
  in front of the character.

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
PANEL_HEIGHT = 370
LEGEND_Y = 345
ORIGIN = (400.0, 270.0)
AXIS_LENGTHS = {"X": 160.0, "Y": 250.0, "Z": 200.0}
# The humanoid is drawn this many times its HUMANOID size, so the live labels have room
SCALE = 1.4
BODY = "#888780"
FORWARD = "#EF9F27"
LEFT = "#7F77DD"

# The character in its own frame: (left side, up, forward) in drawing units
HUMANOID = {
    "head": (0.0, 96.0, 0.0), "neck": (0.0, 84.0, 0.0), "pelvis": (0.0, 40.0, 0.0),
    "left_foot": (12.0, 0.0, 0.0), "right_foot": (-12.0, 0.0, 0.0),
    "left_shoulder": (15.0, 78.0, 0.0), "right_shoulder": (-15.0, 78.0, 0.0),
    "left_hand": (34.0, 52.0, 0.0), "right_hand": (-34.0, 52.0, 0.0),
    "nose": (0.0, 96.0, 30.0),
    # Points just beyond the head top, the nose and the left hand: where the live labels go
    "head_top": (0.0, 110.0, 0.0), "left_beyond": (44.0, 48.0, 0.0),
}
# Live labels: (text, from, towards, distance on screen in px, past the "towards" point or not)
LIVE_LABELS = (("up", "head", "head_top", 30.0, False), ("forward", "head", "nose", 16.0, True),
               ("left", "left_hand", "left_beyond", 16.0, False))
# The forward label hides while the nose is shorter than this on screen (the negation passes through zero)
SHORT_NOSE = 6.0
# Segments: (from, to, colour, width)
SEGMENTS = (
    ("pelvis", "left_foot", BODY, 4.0), ("pelvis", "right_foot", BODY, 4.0), ("neck", "pelvis", BODY, 5.0),
    ("right_shoulder", "left_shoulder", BODY, 4.0), ("right_shoulder", "right_hand", BODY, 3.5),
    ("left_shoulder", "left_hand", LEFT, 3.5),
)
NOSE = ("head", "nose", FORWARD, 3.0)
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
    return {name: tuple(SCALE * (a * left[i] + b * up[i] + c * forward[i]) for i in range(3))
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


def _keyframed(tag, attributes, frames, times, extra, content=""):
    """
    An element whose attributes follow the frames.

    Parameters
    ----------
    tag : str
    attributes : sequence of tuple
        ``(attribute, function of a frame giving its value as text)``.
    frames : list of dict
    times : list of float
    extra : str
        Fixed attributes.
    content : str
        Text inside the element, after the animations.

    Returns
    -------
    str
    """
    first = " ".join(f'{name}="{value(frames[0])}"' for name, value in attributes)
    anims = "".join(_animate(name, [value(f) for f in frames], times) for name, value in attributes)
    return f"<{tag} {first} {extra}>{anims}{content}</{tag}>"


def _segment(start, end, colour, width, frames, times):
    attrs = [(a, (lambda f, point=point, axis=axis: fmt(f[point][axis])))
             for a, point, axis in (("x1", start, 0), ("y1", start, 1), ("x2", end, 0), ("y2", end, 1))]
    return _keyframed("line", attrs, frames, times,
                      f'stroke="{colour}" stroke-width="{fmt(width)}" stroke-linecap="round"')


def label_position(frame, start, towards, distance, past):
    """
    Where a live label goes on screen.

    Parameters
    ----------
    frame : dict
        Screen points of one frame.
    start, towards : str
        The label sits on the line from ``start`` towards ``towards``.
    distance : float
        Pixels from ``start``; with ``past``, pixels beyond ``towards``, and at
        least 30 px from ``start`` so it clears the head.
    past : bool

    Returns
    -------
    tuple of float
        ``(x, y)`` of the text's anchor, 4 px lower to centre it on the line.
    """
    (px, py), (bx, by) = frame[start], frame[towards]
    dx, dy = bx - px, by - py
    length = math.hypot(dx, dy) or 1.0
    reach = max(length + distance, 30.0) if past else distance
    return px + reach * dx / length, py + reach * dy / length + 4


def nose_length(frame):
    """The nose's length on screen in one frame."""
    (hx, hy), (nx, ny) = frame["head"], frame["nose"]
    return math.hypot(nx - hx, ny - hy)


# Live labels get an outline in the page's background colour, so they read over lines
HALO = ("<style>.halo{paint-order:stroke;stroke:#ffffff;stroke-width:4px;stroke-linejoin:round}"
        "@media (prefers-color-scheme: dark){.halo{stroke:#0d1117}}</style>")
LEGEND = ((BODY, "Body"), (FORWARD, "Forward (nose)"), (LEFT, "Left arm and hand"), (RED, "+X"), (GREEN, "+Y"),
          (BLUE, "+Z"))


def animated_panel():
    """
    Fig. 3(a): fixed axes, the moving humanoid with its live labels, the step
    texts and the colour legend.

    The nose is drawn after the head, so the head never covers it.

    Returns
    -------
    list of str
    """
    times = frame_times()
    frames = [{name: to_screen(p) for name, p in character_points(stage_matrix(t)).items()} for t in times]
    body = [HALO]
    for name, colour in (("X", RED), ("Y", GREEN), ("Z", BLUE)):
        end = {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}[name]
        tip = to_screen(tuple(AXIS_LENGTHS[name] * c for c in end))
        body.append(line(ORIGIN[0], ORIGIN[1], tip[0], tip[1], colour, 2.0))
        dx, dy = tip[0] - ORIGIN[0], tip[1] - ORIGIN[1]
        norm = math.hypot(dx, dy)
        body.append(text(tip[0] + 16 * dx / norm, tip[1] + 16 * dy / norm + 4, f"+{name}", "t", "middle"))
    for start, end, colour, width in SEGMENTS:
        body.append(_segment(start, end, colour, width, frames, times))
    for point, radius, colour in (("head", 14, BODY), ("left_hand", 6, LEFT)):
        attrs = [("cx", lambda f, point=point: fmt(f[point][0])), ("cy", lambda f, point=point: fmt(f[point][1]))]
        body.append(_keyframed("circle", attrs, frames, times, f'r="{radius}" fill="{colour}"'))
    body.append(_segment(*NOSE, frames, times))
    heads = [_head_points(f["head"], f["nose"]) for f in frames]
    body.append(f'<polygon points="{heads[0]}" fill="{FORWARD}">{_animate("points", heads, times)}</polygon>')
    for label, start, towards, distance, past in LIVE_LABELS:
        attrs = [("x", lambda f, a=start, b=towards, d=distance, q=past: fmt(label_position(f, a, b, d, q)[0])),
                 ("y", lambda f, a=start, b=towards, d=distance, q=past: fmt(label_position(f, a, b, d, q)[1]))]
        if label == "forward":
            attrs.append(("opacity", lambda f: "1" if nose_length(f) >= SHORT_NOSE else "0"))
        body.append(_keyframed("text", attrs, frames, times, 'class="s halo" text-anchor="middle"', label))
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
    x = 20.0
    for colour, label in LEGEND:
        body.append(line(x, LEGEND_Y, x + 22, LEGEND_Y, colour, 3.0, head=False))
        body.append(text(x + 28, LEGEND_Y + 4, label))
        x += 28 + 7.2 * len(label) + 22
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


def figure_axis_swap_animated():
    """
    Fig. 3(a), the animated part.

    Returns
    -------
    str
    """
    return svg(680, PANEL_HEIGHT, "The axis swap from Blender into FLVER space, animated",
               "Animated over 30 seconds: fixed axes drawn as Blender's Front view shows them, +X to the right, +Z "
               "up and +Y into the scene. A character stands facing the viewer, up +Z, forward -Y, left side +X, "
               "with labels up, forward and left that move with it. Its coordinates are rotated -90 degrees about "
               "X, which lays it on its back, up +Y and forward +Z; then Z is negated, a reflection, which turns "
               "it face down, forward -Z, with the left side still at +X. A text names each step, and a legend "
               "gives the colours: gray body, amber forward (nose), purple left arm and hand, and the three "
               "axes.", animated_panel())


def figure_axis_swap():
    """
    Fig. 3(b), the three static stages.

    Returns
    -------
    str
    """
    return svg(680, 280, "The axis swap from Blender into FLVER space",
               "Three panels show a character's axes seen from in front, with its left side to the right of the "
               "screen. In Blender, X points right, Z up and Y into the screen: right-handed, with forward along "
               "-Y. After a -90 degree rotation about X, Y points up and Z out of the screen: still right-handed, "
               "with forward along +Z. After Z is negated, Z points into the screen: left-handed, as in FLVER, "
               "with forward along -Z and the left side still along +X.", static_panels())
