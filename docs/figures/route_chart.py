"""
The "Ways out of Blender" chart of docs/NORMAL_MAPS.md: the three routes from
Blender into FbxImporter, which with ER Tangents ticked all give a FLVER in the
game's tangent frame.

The boxes are data (``ROUTE_BOXES``), so the tests can check that every label
fits its box without reading the SVG.
"""

from svg_parts import line, svg, text

WIDTH = 680
HEIGHT = 292

TITLE_LINE = 14
LINE_STEP = 18


class Box:
    """
    A box of the chart: its position, size and lines of text.

    Parameters
    ----------
    x, y : float
        Top-left corner.
    width, height : float
        Size.
    lines : tuple of str
        The title (drawn bold), then the lines under it.
    """

    def __init__(self, x, y, width, height, lines):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.lines = lines

    @property
    def middle(self):
        """
        The vertical middle of the box.

        Returns
        -------
        float
        """
        return self.y + self.height / 2


def text_block_height(count):
    """
    The height of a title and ``count - 1`` lines under it.

    Parameters
    ----------
    count : int
        Number of lines, the title included.

    Returns
    -------
    float
    """
    return TITLE_LINE + LINE_STEP * (count - 1)


ROUTE_BOXES = (
    Box(40, 20, 220, 64, ("FLVER Prep export", "no tangents")),
    Box(40, 100, 220, 78, ("Blender FBX export", "Tangent Space off", "no tangents")),
    Box(40, 194, 220, 78, ("Blender FBX export", "Tangent Space on", "+U tangents with no W")),
    Box(320, 107, 170, 64, ("FbxImporter", "ER Tangents ticked")),
    Box(520, 107, 150, 64, ("FLVER", "the game's frame")),
)

BUS_X = 290


def draw_box(box):
    """
    A box with its lines centred in it.

    Parameters
    ----------
    box : Box

    Returns
    -------
    list of str
    """
    body = [f'<rect class="p" x="{box.x}" y="{box.y}" width="{box.width}" height="{box.height}" rx="6" '
            f'stroke-width="0.5"/>']
    top = box.y + (box.height - text_block_height(len(box.lines))) / 2 + 11
    centre = box.x + box.width / 2
    for index, content in enumerate(box.lines):
        body.append(text(centre, top + LINE_STEP * index, content, "t h" if index == 0 else "s", "middle"))
    return body


def figure_ways_out():
    """
    The three routes out of Blender, joined into FbxImporter and on to the
    FLVER.

    Returns
    -------
    str
    """
    sources = ROUTE_BOXES[:3]
    importer, flver = ROUTE_BOXES[3], ROUTE_BOXES[4]
    body = []
    for box in ROUTE_BOXES:
        body += draw_box(box)
    for box in sources:
        body.append(line(box.x + box.width, box.middle, BUS_X, box.middle, None, 1.0, head=False))
    body.append(line(BUS_X, sources[0].middle, BUS_X, sources[-1].middle, None, 1.0, head=False))
    body.append(line(BUS_X, importer.middle, importer.x - 2, importer.middle, None, 1.0))
    body.append(line(importer.x + importer.width, importer.middle, flver.x - 2, flver.middle, None, 1.0))
    return svg(WIDTH, HEIGHT, "Ways out of Blender",
               "Three routes from Blender into FbxImporter: FLVER Prep's export, with no tangents; Blender's FBX "
               "export with Tangent Space off, with no tangents; and Blender's FBX export with Tangent Space on, "
               "with tangents along +U and no W. With ER Tangents ticked, FbxImporter writes a FLVER whose "
               "tangents follow the game's frame, whichever route the file took.", body)
