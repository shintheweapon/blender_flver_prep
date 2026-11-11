"""
Write the figures of docs/NORMAL_MAPS.md.

Run ``python docs/figures/make_figures.py`` from the repository folder to
rewrite the SVG files next to this script. The geometry comes from
``tangent_geometry``, the shared drawing parts from ``svg_parts`` and the
route chart from ``route_chart``; this module draws the tangent figures. The tests check that the
committed files equal what this script writes.
"""

import os

from route_chart import figure_ways_out
from svg_parts import BLUE, GREEN, RED, fmt, legend, line, svg, text
from tangent_geometry import (CASES, MOTION, NORMAL, V, cross_as_drawn, decode, dome_points, dot, read_directions,
                              to_3d, vanilla_sign)

FIGURES_DIR = os.path.dirname(os.path.abspath(__file__))

# Perspective sheets: +x right, +y up, +z towards the viewer.
DEPTH_X = -0.35
DEPTH_Y = 0.5


def project(origin, point):
    """
    Screen position of a drawn 3D point.

    Parameters
    ----------
    origin : tuple of float
        Screen position of the sheet's far-left corner (3D origin).
    point : tuple of float
        ``(x, y, z)``.

    Returns
    -------
    tuple of float
    """
    x, y, z = point
    return origin[0] + x + DEPTH_X * z, origin[1] - y + DEPTH_Y * z


def sheet(origin, size, mirrored):
    """
    A flat sheet with its +U and +V axes and the "row 0" label.

    Parameters
    ----------
    origin : tuple of float
        Screen position of the far-left corner.
    size : float
        Width and depth of the sheet.
    mirrored : bool
        True when +U runs to the left.

    Returns
    -------
    list of str
    """
    corners = [project(origin, p) for p in ((0, 0, 0), (size, 0, 0), (size, 0, size), (0, 0, size))]
    points = " ".join(f"{fmt(x)},{fmt(y)}" for x, y in corners)
    far_left, far_right = corners[0], corners[1]
    near_left = corners[3]
    body = [f'<polygon class="p" points="{points}" stroke-width="0.5"/>']
    if mirrored:
        body.append(line(far_right[0] - 8, far_right[1] - 12, far_left[0] + 8, far_left[1] - 12, None, 1.0))
        body.append(text(far_left[0] - 4, far_left[1] - 8, "+U", anchor="end"))
    else:
        body.append(line(far_left[0] + 8, far_left[1] - 12, far_right[0] - 8, far_right[1] - 12, None, 1.0))
        body.append(text(far_right[0] + 4, far_right[1] - 8, "+U"))
    body.append(line(far_left[0] - 14, far_left[1] + 4, near_left[0] - 14, near_left[1] - 4, None, 1.0))
    body.append(text(near_left[0] - 18, near_left[1] + 16, "+V", anchor="middle"))
    body.append(text(far_right[0] - 6, far_left[1] - 24, "row 0", anchor="end"))
    return body


def arrow_3d(origin, start, direction, length, colour, width=2.0, dashed=False):
    """
    An arrow from a 3D point along a 3D direction.

    Returns
    -------
    str
    """
    end = tuple(s + length * d for s, d in zip(start, direction))
    x1, y1 = project(origin, start)
    x2, y2 = project(origin, end)
    return line(x1, y1, x2, y2, colour, width, dashed, head=not dashed)


def figure_layout():
    """
    The layout of a normal map: U right, V down, red and green, a bump.

    Returns
    -------
    str
    """
    body = [
        '<rect class="p" x="80" y="60" width="220" height="220" rx="4" stroke-width="0.5"/>',
        line(90, 40, 290, 40, RED),
        text(306, 44, "+U", "t h"),
        line(58, 70, 58, 270, GREEN),
        text(58, 298, "+V", "t h", "middle"),
        text(92, 82, "(0, 0), row 0"),
        '<circle cx="190" cy="175" r="48" fill="none" class="o" stroke-width="1" stroke-dasharray="3 3"/>',
        text(190, 179, "bump", anchor="middle"),
        line(226, 175, 270, 175, RED),
        line(190, 211, 190, 258, GREEN),
        text(340, 96, "Red: the surface tilts towards +U", "t h"),
        text(340, 128, "Green: the surface tilts towards +V", "t h"),
        text(340, 148, "V runs down the image (DirectX layout)"),
        text(340, 180, "Blue: gloss. Alpha: other data", "t h"),
        text(340, 200, "Neither is part of the normal"),
        text(340, 240, "On a raised bump, red is high on its +U side"),
        text(340, 258, "and green is high on its +V side"),
    ]
    return svg(680, 320, "The layout of a normal map",
               "A texture with U running right and V running down from row 0 at the top. Red stores how far "
               "the surface tilts towards +U, green how far it tilts towards +V. Blue holds gloss and alpha "
               "other data. On a raised bump, red is high on its +U side and green on its +V side.", body)


def figure_tangent_frame():
    """
    The vanilla tangent frame on an unmirrored and a mirrored island, in
    perspective.

    Returns
    -------
    str
    """
    body = []
    for mirrored, origin, title in ((False, (110, 120), "Unmirrored island"),
                                    (True, (440, 120), "Mirrored island")):
        body += sheet(origin, 160, mirrored)
        centre = (80.0, 0.0, 80.0)
        sign = vanilla_sign(mirrored)
        tangent = to_3d(V, mirrored)
        n_x_t = cross_as_drawn(NORMAL, tangent)
        body.append(arrow_3d(origin, centre, NORMAL, 84, None))
        cx, cy = project(origin, centre)
        body.append(text(cx + 10, cy - 80, "N"))
        body.append(arrow_3d(origin, centre, tangent, 66, GREEN))
        if sign < 0:
            body.append(arrow_3d(origin, centre, n_x_t, 52, RED, 1.0, dashed=True))
        body.append(arrow_3d(origin, centre, tuple(sign * c for c in n_x_t), 64, RED))
        body.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="3" class="of"/>')
        body.append(text(cx - 2, 246, f"{title}, W = {'+1' if sign > 0 else '−1'}", "t h", "middle"))
    body += legend(70, 284, GREEN, "T, along +V")
    body += legend(200, 284, RED, "W(N × T), along +U")
    body.append(line(380, 284, 404, 284, RED, 1.0, dashed=True, head=False))
    body.append(text(410, 288, "N × T (left-hand rule)"))
    return svg(680, 310, "The tangent frame on the game's own models",
               "Two UV islands lying flat, as seen in game, with N pointing up and T along +V towards the "
               "viewer. In FLVER's left-handed space N x T follows the left-hand rule and points left. On the "
               "unmirrored island +U runs right, so W = -1 turns N x T to point along +U. On the mirrored "
               "island +U runs left, N x T already points along +U, and W = +1.", body)


TITLES = (
    ("Vanilla tangents", "as the game's own", "models store them"),
    ("FbxImporter", "1.11.0: Transform None", "1.7.0 to 1.10.2: Mirror unticked"),
    ("FbxImporter", "1.11.0: Transform Mirror Z", "1.7.0 to 1.10.2: Mirror ticked"),
)

NOTE = ("In 1.3 to 1.6.1, Mirror unticked reads as the middle column;",
        "Mirror ticked mirrored X instead (not shown).")


def panel_titles(cx, y, titles):
    """
    A panel's three title lines.

    Returns
    -------
    list of str
    """
    first, second, third = titles
    return [text(cx, y, first, "t h", "middle"), text(cx, y + 20, second, anchor="middle"),
            text(cx, y + 36, third, anchor="middle")]


def figure_fbximporter_tangents():
    """
    The directions the game reads green and red in each case, in
    perspective.

    Returns
    -------
    str
    """
    body = []
    for index, case in enumerate(CASES):
        origin = (100 + 220 * index, 100)
        body += sheet(origin, 120, False)
        centre = (60.0, 0.0, 60.0)
        green, red = read_directions(case)
        body.append(arrow_3d(origin, centre, NORMAL, 64, None))
        cx, cy = project(origin, centre)
        body.append(text(cx - 8, cy - 54, "N", anchor="end"))
        body.append(arrow_3d(origin, centre, to_3d(green, False), 50 if green[0] else 66, GREEN))
        body.append(arrow_3d(origin, centre, to_3d(red, False), 50 if red[0] else 66, RED))
        body.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="3" class="of"/>')
        body += panel_titles(cx, 220, TITLES[index])
    body += legend(60, 290, GREEN, "T: the game reads green along it")
    body += legend(330, 290, RED, "W(N × T): the game reads red along it")
    body.append(text(340, 318, NOTE[0], anchor="middle"))
    body.append(text(340, 334, NOTE[1], anchor="middle"))
    return svg(680, 350, "The directions the game reads green and red",
               "Three sheets lying flat with N up, +U to the right and +V towards the viewer. Vanilla "
               "tangents: green is read along +V and red along +U. FbxImporter 1.11.0 Transform None (1.7.0 "
               "to 1.10.2 Mirror unticked): green along +U and red along -V, a quarter turn. FbxImporter "
               "1.11.0 Transform Mirror Z (1.7.0 to 1.10.2 Mirror ticked): green along +U and red along +V, "
               "red and green swapped.", body)



ANIMATION = """<style>
.spin{transform:rotate(-90deg)}
.flip{transform:rotate(45deg) scale(1,-1) rotate(-45deg)}
@media (prefers-reduced-motion: no-preference){
.spin{animation:spin 5s linear infinite}
.flip{animation:flip 5s linear infinite}
}
@keyframes spin{0%,20%{transform:rotate(0deg)}45%,80%{transform:rotate(-90deg)}100%{transform:rotate(0deg)}}
@keyframes flip{0%,20%{transform:rotate(45deg) scale(1,1) rotate(-45deg)}45%,80%{transform:rotate(45deg) scale(1,-1) rotate(-45deg)}100%{transform:rotate(45deg) scale(1,1) rotate(-45deg)}}
</style>"""

def moving(x, y, motion, parts):
    """
    Elements drawn from a point, turning or flipping about it.

    The elements are drawn as in the game's frame; the animation turns them
    a quarter (Transform None) or flips them across the U = V diagonal
    (Mirror Z). Without motion they show where they end.

    Returns
    -------
    str
    """
    inner = "".join(parts)
    if motion is None:
        return f'<g transform="translate({fmt(x)},{fmt(y)})">{inner}</g>'
    return f'<g transform="translate({fmt(x)},{fmt(y)})"><g class="{motion}">{inner}</g></g>'


def figure_dome_tilts():
    """
    The tilts the game decodes around a raised dome in each case, animated
    from the vanilla frame into each case's frame.

    Returns
    -------
    str
    """
    body = [ANIMATION]
    for index, case in enumerate(CASES):
        cx, cy = 130 + 220 * index, 160
        motion = MOTION[case.key]
        body.append(moving(cx, 40, motion, [line(0, 0, 0, 26, GREEN), line(0, 0, 26, 0, RED)]))
        if index == 0:
            body.append(text(cx - 34, 44, "Frame", anchor="end"))
        body.append(f'<circle cx="{cx}" cy="{cy}" r="40" fill="none" class="o" stroke-width="0.5" '
                    f'stroke-dasharray="3 3"/>')
        if case.key == "mirror_z":
            body.append(f'<line x1="{cx - 45}" y1="{cy - 45}" x2="{cx + 45}" y2="{cy + 45}" class="o" '
                        f'stroke-width="0.5" stroke-dasharray="2 4"/>')
        for direction in dome_points():
            decoded = decode(direction, case)
            colour = None
            if case.key == "mirror_z":
                along = dot(decoded, direction)
                if along > 1e-6:
                    colour = RED
                elif along < -1e-6:
                    colour = BLUE
            px, py = cx + 40 * direction[0], cy + 40 * direction[1]
            body.append(moving(px, py, motion,
                               [line(0, 0, 18 * direction[0], 18 * direction[1], colour, 1.5)]))
        body += panel_titles(cx, 248, TITLES[index])
        outcome = ("Dome reads raised", "Tilts turn a quarter: twisted", "Tilts flip on the diagonal")[index]
        body.append(text(cx, 306, outcome, anchor="middle"))
    body += legend(40, 338, GREEN, "T: the game reads green along it")
    body += legend(300, 338, RED, "W(N × T): the game reads red along it")
    body += legend(40, 364, None, "Surface tilt the game decodes", head=True)
    body += legend(300, 364, RED, "On the diagonal: stays out (raised)", head=True)
    body += legend(540, 364, BLUE, "Turns in (dented)", head=True)
    body.append(text(340, 394, NOTE[0], anchor="middle"))
    body.append(text(340, 410, NOTE[1], anchor="middle"))
    return svg(680, 424, "The tilts the game decodes around a raised dome",
               "Animated. Three panels, each with the frame (green T, red W(N x T)) and the surface tilts the "
               "game decodes around a raised dome. Vanilla tangents: the tilts point outward and the dome "
               "reads raised. FbxImporter 1.11.0 Transform None (1.7.0 to 1.10.2 Mirror unticked): the frame "
               "and every tilt turn a quarter, so the tilts run round the dome. FbxImporter 1.11.0 Transform "
               "Mirror Z (1.7.0 to 1.10.2 Mirror ticked): the frame and every tilt flip across the U = V "
               "diagonal, so the tilts on the diagonal stay outward (raised) and the others turn inward "
               "(dented).", body)


FIGURES = {
    "normal_map_layout.svg": figure_layout,
    "tangent_frame.svg": figure_tangent_frame,
    "fbximporter_tangents.svg": figure_fbximporter_tangents,
    "dome_tilts.svg": figure_dome_tilts,
    "ways_out_of_blender.svg": figure_ways_out,
}


def build_all():
    """
    Every figure's SVG text.

    Returns
    -------
    dict
        File name to SVG text.
    """
    return {name: make() for name, make in FIGURES.items()}


def main():
    """
    Write every figure next to this script.
    """
    for name, content in build_all().items():
        with open(os.path.join(FIGURES_DIR, name), "w", encoding="utf-8", newline="\n") as file:
            file.write(content)


if __name__ == "__main__":
    main()
