"""
Maths as pictures in the Word file, for viewers that do not show Word
equations.

``export_docx.py --math-images`` has pandoc parse the paper into its JSON tree;
every maths node (``Math``) is drawn once by KaTeX in headless Chrome
(``render``), replaced by a picture (``replace_math``), and pandoc writes the
Word file from the tree. After pandoc, ``place_math`` sets each inline
picture on the text's baseline and gives each display equation its number at
the right margin. Only ``render`` needs Chrome; the other steps are pure.
"""

import hashlib
import html
import re

import docx_xml
from docx_tables import CENTRE

B = "\\"
NUMBER = re.compile(r"\s*" + re.escape(B + "qquad") + r"\s*\((\d+)\)\s*$")
# KaTeX's size against 12 pt body text (16 px), and how much sharper than 96 px an inch each picture is captured
MATH_EM = 1.1
CAPTURE_SCALE = 4
PIXELS_PER_INCH = 96.0
# Room a display equation leaves for its number at the right margin
NUMBER_ROOM_INCHES = 0.6


def split_number(tex):
    """
    A display equation's TeX without its number, and the number.

    ``prepare_markdown`` turns ``\\tag{n}`` into a trailing ``\\qquad (n)``.

    Parameters
    ----------
    tex : str

    Returns
    -------
    tuple
        ``(tex, number)``; the number is a str, or None when there is none.
    """
    found = NUMBER.search(tex)
    if not found:
        return tex.strip(), None
    return tex[:found.start()].strip(), found.group(1)


def math_nodes(tree):
    """
    Every maths node of a pandoc JSON tree, in document order.

    Parameters
    ----------
    tree : dict or list
        pandoc's JSON tree, or part of it.

    Returns
    -------
    list of tuple
        ``(kind, tex)``, kind ``"inline"`` or ``"display"``; a display
        equation's TeX keeps its number (``split_number``).
    """
    found = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("t") == "Math":
                kind = "display" if node["c"][0]["t"] == "DisplayMath" else "inline"
                found.append((kind, node["c"][1]))
                return
            walk(node.get("c", node.get("blocks")))  # the tree's top keeps its blocks under "blocks"
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(tree)
    return found


def image_name(kind, tex):
    """
    The file a maths expression is drawn into: one per distinct expression.

    Parameters
    ----------
    kind : str
        ``"inline"`` or ``"display"``.
    tex : str
        Without a display equation's number.

    Returns
    -------
    str
        ``math_i_<hash>.png`` or ``math_d_<hash>.png``.
    """
    digest = hashlib.sha1(f"{kind}\n{tex.strip()}".encode("utf-8")).hexdigest()[:12]
    return f"math_{kind[0]}_{digest}.png"


def distinct_items(tree):
    """
    The distinct expressions of a tree, in first-use order, numbers left off.

    Parameters
    ----------
    tree : dict

    Returns
    -------
    list of tuple
        ``(name, kind, tex)``.
    """
    items, seen = [], set()
    for kind, tex in math_nodes(tree):
        tex = split_number(tex)[0] if kind == "display" else tex.strip()
        name = image_name(kind, tex)
        if name not in seen:
            seen.add(name)
            items.append((name, kind, tex))
    return items


def math_page(items, katex_head):
    """
    A white page holding every expression for KaTeX to draw, each in its own box.

    Each box (``.w``) holds the maths and, after it, a zero-size marker
    (``.b``) whose top is the text's baseline. Chinese inside ``\\text{}``
    falls back to Source Han Sans SC, then Noto Sans SC. The page defines the
    hooks ``chrome.Chrome`` and ``render`` call: ``window.ready``,
    ``window.boxes()`` and ``window.errors()``.

    Parameters
    ----------
    items : list of tuple
        ``(name, kind, tex)`` (``distinct_items``).
    katex_head : str
        The tags that load KaTeX (``scenes.KATEX_HEAD``).

    Returns
    -------
    str
    """
    boxes = "".join(
        f'<div class="m"><span class="w"><span data-tex="{html.escape(tex, quote=True)}" '
        f'data-display="{1 if kind == "display" else 0}"></span><span class="b"></span></span></div>\n'
        for _, kind, tex in items)
    return ("<!doctype html><html><head><meta charset='utf-8'>" + katex_head
            + "<style>html,body{margin:0;background:#ffffff;color:#000000}body{font-size:16px;padding:8px}"
            ".m{margin:0 0 24px 0}.w{display:inline-block;padding:2px}"
            f".katex{{font-size:{MATH_EM}em;font-family:KaTeX_Main,'Source Han Sans SC','Noto Sans SC',serif}}"
            ".katex .cjk_fallback{font-family:'Source Han Sans SC','Noto Sans SC',sans-serif}"
            ".katex-display{margin:0}.b{display:inline-block;width:0;height:0}</style></head><body>\n"
            + boxes + "<script>"
            "window.ready=(async()=>{for(const e of document.querySelectorAll('[data-tex]')){"
            "katex.render(e.dataset.tex,e,{displayMode:e.dataset.display==='1',throwOnError:false});}"
            "await document.fonts.ready;"
            "await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return true})();"
            "window.boxes=()=>[...document.querySelectorAll('.w')].map(w=>{const r=w.getBoundingClientRect(),"
            "b=w.querySelector('.b').getBoundingClientRect();"
            "return [r.left+scrollX,r.top+scrollY,r.width,r.height,b.top+scrollY];});"
            "window.errors=()=>document.querySelectorAll('.katex-error').length;"
            "window.setTime=async t=>t;</script></body></html>")


def picture_size(kind, width, height, bottom_to_baseline, text_inches):
    """
    A drawn expression's size in the Word file, from its box in pixels.

    Parameters
    ----------
    kind : str
    width, height : float
        The box, in CSS pixels (96 an inch).
    bottom_to_baseline : float
        Pixels from the baseline down to the box's bottom.
    text_inches : float
        The text width; a display equation is scaled down to fit it less
        ``NUMBER_ROOM_INCHES``.

    Returns
    -------
    tuple
        ``(width_in, height_in, depth_pt, scaled)``: inches, inches, points
        below the baseline (0 for display equations), and whether it was
        scaled down.
    """
    width_in, height_in = width / PIXELS_PER_INCH, height / PIXELS_PER_INCH
    room = text_inches - NUMBER_ROOM_INCHES
    if kind == "display":
        if width_in > room:
            return room, height_in * room / width_in, 0.0, True
        return width_in, height_in, 0.0, False
    return width_in, height_in, max(0.0, bottom_to_baseline) * 72.0 / PIXELS_PER_INCH, False


def image_node(name, tex, size):
    """A pandoc ``Image`` node for a drawn expression: the TeX as its alt text, its size in inches."""
    width_in, height_in = size[0], size[1]
    attributes = [["width", f"{width_in:.3f}in"], ["height", f"{height_in:.3f}in"]]
    return {"t": "Image", "c": [["", [], attributes], [{"t": "Str", "c": tex}], [f"math/{name}", ""]]}


def replace_math(tree, sizes):
    """
    The tree with every maths node replaced by its picture.

    A paragraph holding a display equation keeps only the picture.

    Parameters
    ----------
    tree : dict
        pandoc's JSON tree; left unchanged.
    sizes : dict
        Picture name to ``(width_in, height_in, ...)`` (``picture_size``).

    Returns
    -------
    tuple
        ``(tree, numbers)``: the new tree, and the display equations' numbers
        in order (None where one has none).

    Raises
    ------
    KeyError
        For an expression with no size, that is, not drawn.
    """
    numbers = []

    def picture(node):
        kind = "display" if node["c"][0]["t"] == "DisplayMath" else "inline"
        tex = node["c"][1]
        if kind == "display":
            tex, number = split_number(tex)
            numbers.append(number)
        else:
            tex = tex.strip()
        name = image_name(kind, tex)
        return image_node(name, tex, sizes[name])

    def walk(node):
        if isinstance(node, list):
            return [walk(child) for child in node]
        if not isinstance(node, dict):
            return node
        if node.get("t") == "Math":
            return picture(node)
        if node.get("t") == "Para" and any(child.get("t") == "Math" and child["c"][0]["t"] == "DisplayMath"
                                           for child in node["c"]):
            return {"t": "Para", "c": [picture(child) for child in node["c"]
                                       if child.get("t") == "Math"]}
        if "c" in node:
            return dict(node, c=walk(node["c"]))
        if "blocks" in node:
            return dict(node, blocks=walk(node["blocks"]))
        return node

    return walk(tree), numbers


INLINE_RUN = re.compile(r"<w:r>(?:(?!</w:r>).)*?<w:drawing>(?:(?!</w:r>).)*?descr=\"(?:math/)?(math_i_[0-9a-f]{12}"
                        r"\.png)\"(?:(?!</w:r>).)*</w:r>", re.S)
DISPLAY_NAME = re.compile(r"descr=\"(?:math/)?(math_d_[0-9a-f]{12}\.png)\"")
# Paragraph properties a w:tabs comes before, in schema order
AFTER_TABS = ("<w:suppressAutoHyphens", "<w:kinsoku", "<w:wordWrap", "<w:overflowPunct", "<w:topLinePunct",
              "<w:autoSpaceDE", "<w:autoSpaceDN", "<w:bidi", "<w:adjustRightInd", "<w:snapToGrid", "<w:spacing",
              "<w:ind", "<w:contextualSpacing", "<w:mirrorIndents", "<w:suppressOverlap", "<w:jc", "<w:textDirection",
              "<w:textAlignment", "<w:textboxTightWrap", "<w:outlineLvl", "<w:divId", "<w:cnfStyle", "<w:rPr>",
              "<w:sectPr", "<w:pPrChange")


def place_math(document_xml, sizes, numbers, text_width):
    """
    Set the maths pictures in their lines, after pandoc.

    - A run holding an inline picture gets ``<w:position>``, lowering it by its
      depth (half-points), so the maths sits on the text's baseline.
    - A paragraph holding a display picture gets a centre tab at half the text
      width and a right tab at the text width, a tab before the picture, and a
      tab and its number, as ``(n)``, after it; the numbers are taken in order.

    Running it again changes nothing.

    Parameters
    ----------
    document_xml : str
    sizes : dict
        Picture name to ``(width_in, height_in, depth_pt, scaled)``.
    numbers : list
        The display equations' numbers in document order (``replace_math``).
    text_width : int
        Twips.

    Returns
    -------
    str
    """
    def inline(match):
        xml = match.group(0)
        if "<w:position" in xml:
            return xml
        position = f'<w:position w:val="{-int(round(sizes[match.group(1)][2] * 2))}"/>'
        if xml.startswith("<w:r><w:rPr>"):
            size = xml.find("<w:sz ")
            at = size if 0 <= size < xml.index("</w:rPr>") else xml.index("</w:rPr>")
            return xml[:at] + position + xml[at:]
        return "<w:r><w:rPr>" + position + "</w:rPr>" + xml[len("<w:r>"):]

    document_xml = INLINE_RUN.sub(inline, document_xml)
    remaining = iter(numbers)
    tabs = (f'<w:tabs><w:tab w:val="center" w:pos="{text_width // 2}"/>'
            f'<w:tab w:val="right" w:pos="{text_width}"/></w:tabs>')

    def display(match):
        xml = match.group(0)
        if not DISPLAY_NAME.search(xml):
            return xml
        number = next(remaining, None)
        if "<w:tabs>" in xml:
            return xml
        xml = xml.replace(CENTRE, "")
        if not xml.startswith("<w:p><w:pPr>"):
            xml = "<w:p><w:pPr></w:pPr>" + xml[len("<w:p>"):]
        end = xml.index("</w:pPr>")
        at = min([xml.find(tag, 0, end) for tag in AFTER_TABS if 0 <= xml.find(tag, 0, end)] + [end])
        xml = xml[:at] + tabs + xml[at:]
        run = xml.index("<w:r>", xml.index("</w:pPr>"))
        close = xml.index("</w:r>", xml.index("<w:drawing>")) + len("</w:r>")
        after = "<w:r><w:tab/>" + (f"<w:t>({number})</w:t>" if number else "") + "</w:r>"
        return xml[:run] + "<w:r><w:tab/></w:r>" + xml[run:close] + after + xml[close:]

    return docx_xml.PARAGRAPH.sub(display, document_xml)

