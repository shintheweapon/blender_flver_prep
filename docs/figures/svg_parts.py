"""
Shared building blocks for the SVG figures of docs/NORMAL_MAPS.md: the colours,
the style that follows the viewer's light or dark theme, the arrow heads, and
helpers for lines, text, legends and whole documents.
"""

RED = "#E24B4A"
GREEN = "#639922"
BLUE = "#378ADD"



STYLE = """<style>
.t{fill:#1f2328;font:14px -apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
.h{font-weight:600}
.s{fill:#59636e;font:12px -apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
.o{stroke:#59636e}
.of{fill:#59636e}
.p{fill:#f6f8fa;stroke:#8c959f}
.g{stroke:#8c959f}
@media (prefers-color-scheme: dark){
.t{fill:#e6edf3}
.s{fill:#9198a1}
.o{stroke:#9198a1}
.of{fill:#9198a1}
.p{fill:#151b23;stroke:#656c76}
.g{stroke:#656c76}
}
</style>"""

MARKERS = ('<defs>'
           f'<marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
           f'orient="auto"><path d="M1 1L9 5L1 9z" fill="{RED}"/></marker>'
           f'<marker id="ag" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
           f'orient="auto"><path d="M1 1L9 5L1 9z" fill="{GREEN}"/></marker>'
           f'<marker id="ab" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
           f'orient="auto"><path d="M1 1L9 5L1 9z" fill="{BLUE}"/></marker>'
           '<marker id="ao" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" '
           'orient="auto"><path class="of" d="M1 1L9 5L1 9z"/></marker>'
           '</defs>')

ARROW = {RED: "ar", GREEN: "ag", BLUE: "ab", None: "ao"}


def fmt(value):
    """
    A coordinate as short text: at most one decimal, no trailing zeros.

    Returns
    -------
    str
    """
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def svg(width, height, title, desc, body):
    """
    A whole SVG document with the shared style and arrow heads.

    Parameters
    ----------
    width, height : int
        Size in pixels.
    title, desc : str
        Accessible name and description.
    body : list of str
        The drawing's elements.

    Returns
    -------
    str
    """
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        f"<title>{title}</title>",
        f"<desc>{desc}</desc>",
        STYLE,
        MARKERS,
        *body,
        "</svg>",
    ]) + "\n"


def line(x1, y1, x2, y2, colour=None, width=2.0, dashed=False, head=True, extra=""):
    """
    A straight line, coloured or in the theme's outline colour.

    Returns
    -------
    str
    """
    paint = f'stroke="{colour}"' if colour else 'class="o"'
    dash = ' stroke-dasharray="4 3"' if dashed else ""
    marker = f' marker-end="url(#{ARROW[colour]})"' if head else ""
    return (f'<line x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" {paint} '
            f'stroke-width="{fmt(width)}"{dash}{marker}{extra}/>')


def text(x, y, content, cls="s", anchor="start"):
    """
    A text label.

    Returns
    -------
    str
    """
    return f'<text class="{cls}" x="{fmt(x)}" y="{fmt(y)}" text-anchor="{anchor}">{content}</text>'


def legend(x, y, colour, label, head=False):
    """
    A legend entry: a short line, then its label.

    Returns
    -------
    list of str
    """
    return [line(x, y, x + 24, y, colour, 2.0, head=head), text(x + 30, y + 4, label)]


def out_of_screen(x, y, r=7.0):
    """
    The symbol for a direction out of the screen, towards the viewer: a
    circle with a dot.

    Returns
    -------
    list of str
    """
    return [f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="none" class="o" stroke-width="1.5"/>',
            f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r / 3)}" class="of"/>']


def into_screen(x, y, r=7.0):
    """
    The symbol for a direction into the screen, away from the viewer: a
    circle with a cross.

    Returns
    -------
    list of str
    """
    d = r * 0.7
    return [f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="none" class="o" stroke-width="1.5"/>',
            line(x - d, y - d, x + d, y + d, None, 1.5, head=False),
            line(x - d, y + d, x + d, y - d, None, 1.5, head=False)]
