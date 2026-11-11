"""
The figures drawn only for the paper docs/paper/ER_NORMAL_MAPS.md: the axis
swap from Blender into FLVER space, the layout test on vanilla maps, one
triangle's UV derivatives and tangent frame, and the channel changes.

``make_figures`` registers and writes them; the geometry comes from ``axes``
and ``tangent_geometry``, the drawing parts from ``svg_parts``.
"""

from axes import BLENDER_TO_FLVER, IDENTITY, ROTATE_X_MINUS_90, character_axes
from svg_parts import into_screen, line, out_of_screen, svg, text

AXIS_STAGES = (
    ("Blender", IDENTITY),
    ("Rotated −90° about X", ROTATE_X_MINUS_90),
    ("Then Z negated: FLVER", BLENDER_TO_FLVER),
)


def signed(name):
    """An axis name with a typographic minus sign."""
    return name.replace("-", "−")


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
