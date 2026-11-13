"""
The Word package's XML, after pandoc: the tables' borders, centring and
unsplittable rows, the rewrite of a part inside the ``.docx`` file, and the
check of what the file holds. ``export_docx.py`` prepares the paper and its
figures and calls these.
"""

import io
import re
import zipfile

B = "\\"

BORDER_EDGES = ("top", "left", "bottom", "right", "insideH", "insideV")
TABLE_BORDERS = ("<w:tblBorders>" + "".join(f'<w:{edge} w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
                                            for edge in BORDER_EDGES) + "</w:tblBorders>")
TABLE_PROPERTIES = re.compile(r"<w:tblPr>(.*?)</w:tblPr>", re.S)


# Word's schema fixes the order of a table's properties
TABLE_PROPERTY_ORDER = ("tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
                        "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd",
                        "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription")
CELL_BORDERS = ("<w:tcPr><w:tcBorders>" + "".join(f'<w:{edge} w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
                                                  for edge in BORDER_EDGES[:4]) + "</w:tcBorders></w:tcPr>")
CENTRE = '<w:jc w:val="center"/>'
CAPTION_STYLE = '<w:pStyle w:val="TableCaption" />'


def child_elements(xml):
    """
    The top-level elements of a run of WordprocessingML, in order.

    Parameters
    ----------
    xml : str
        The inside of a property block, such as a ``tblPr``.

    Returns
    -------
    list of tuple
        ``(local name, element text)``.
    """
    found, depth, start, name = [], 0, None, None
    for match in re.finditer(r"<(/?)w:(\w+)\b[^>]*?(/?)>", xml):
        closing, tag, empty = match.groups()
        if not closing and depth == 0:
            start, name = match.start(), tag
        if not closing and not empty:
            depth += 1
        elif closing:
            depth -= 1
        if depth == 0 and start is not None:
            found.append((name, xml[start:match.end()]))
            start = None
    return found


def table_properties(match):
    """
    A table's ``tblPr`` rebuilt in schema order: centred, as wide as its columns
    when it was set to the full width, with a grid, and without a first-row look.
    """
    parts = dict(child_elements(match.group(1)))
    if 'w:type="pct"' in parts.get("tblW", ""):
        parts["tblW"] = '<w:tblW w:type="auto" w:w="0"/>'
    parts["jc"] = CENTRE
    parts["tblBorders"] = TABLE_BORDERS
    if "tblLook" in parts:
        parts["tblLook"] = parts["tblLook"].replace('w:firstRow="1"', 'w:firstRow="0"')
    return "<w:tblPr>" + "".join(parts[name] for name in TABLE_PROPERTY_ORDER if parts.get(name)) + "</w:tblPr>"


def table_rows(table_xml):
    """
    A table's rows made to stay together: borders on every cell, rows that don't
    split, every row but the last kept with the next, and a bold header row.
    """
    rows = list(re.finditer(r"<w:tr>(.*?)</w:tr>", table_xml, re.S))
    pieces, last = [], 0
    for index, row in enumerate(rows):
        body = re.sub(r"<w:tc>(?!<w:tcPr>)", "<w:tc>" + CELL_BORDERS, row.group(1))
        body = re.sub(r"^(?!<w:trPr>)", "<w:trPr><w:cantSplit/></w:trPr>", body)
        if index < len(rows) - 1:
            body = re.sub(r'(<w:pStyle w:val="[^"]*" />)(?!<w:keepNext/>)', r"\1<w:keepNext/>", body)
        if index == 0:
            body = re.sub(r"<w:r>(?!<w:rPr>)", "<w:r><w:rPr><w:b/></w:rPr>", body)
            body = re.sub(r"<w:r><w:rPr>(?!<w:b/>)", "<w:r><w:rPr><w:b/>", body)
        pieces.append(table_xml[last:row.start()] + "<w:tr>" + body + "</w:tr>")
        last = row.end()
    return "".join(pieces) + table_xml[last:]


def format_tables(document_xml):
    """
    Lay out every table for Word and Google Docs.

    pandoc's tables name a style its Word output doesn't define, so they have no
    lines, fill the page width and may split across pages. Each table here gets:

    - its properties in schema order: centred, as wide as its columns, a grid of
      single 0.5 pt lines, and no first-row look;
    - the same lines on every cell, which a first-row look can't override;
    - rows that don't split, and every row but the last kept with the next, so
      a table moves to the next page whole;
    - a bold header row;

    and each table caption is centred. Running it again changes nothing.

    Parameters
    ----------
    document_xml : str
        ``word/document.xml``.

    Returns
    -------
    str
    """
    def table(match):
        return table_rows(TABLE_PROPERTIES.sub(table_properties, match.group(0), count=1))

    document_xml = re.sub(r"<w:tbl>.*?</w:tbl>", table, document_xml, flags=re.S)
    return re.sub(re.escape(CAPTION_STYLE) + r"(?!" + re.escape(CENTRE) + ")", CAPTION_STYLE + CENTRE, document_xml)


def rewrite_document(path, change):
    """
    Apply ``change`` to ``word/document.xml`` inside a Word file, keeping every
    other part as it is and in the same order.

    Parameters
    ----------
    path : str
    change : callable
        Takes and returns the document XML as text.
    """
    with zipfile.ZipFile(path) as package:
        parts = [(info, package.read(info.filename)) for info in package.infolist()]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as package:
        for info, data in parts:
            if info.filename == "word/document.xml":
                data = change(data.decode("utf-8")).encode("utf-8")
            package.writestr(info, data)
    with open(path, "wb") as file:
        file.write(buffer.getvalue())


def check_docx(path):
    """
    What the Word file holds, to compare with the paper.

    Parameters
    ----------
    path : str

    Returns
    -------
    dict
        ``equations``; ``tables``, ``bordered_tables``, ``centred_tables`` and
        ``centred_captions``; ``cells`` and ``bordered_cells``; ``rows`` and
        ``unsplittable_rows``; ``bold_header_runs``; ``images`` and ``gifs``;
        ``tex_left`` (TeX commands left in the text); ``author`` (the file's
        author field).
    """
    with zipfile.ZipFile(path) as package:
        document = package.read("word/document.xml").decode("utf-8")
        media = [n for n in package.namelist() if n.startswith("word/media/")]
        core = package.read("docProps/core.xml").decode("utf-8")
    text_only = re.sub(r"<m:oMath.*?</m:oMath>", "", document, flags=re.S)
    author = re.search(r"<dc:creator>(.*?)</dc:creator>", core)
    return {
        "equations": len(re.findall(r"<m:oMath[ >]", document)),
        "tables": document.count("<w:tbl>"),
        "bordered_tables": len(re.findall(r"<w:tblPr>(?:(?!</w:tblPr>).)*<w:tblBorders>", document, flags=re.S)),
        "centred_tables": len(re.findall(r"<w:tblPr>(?:(?!</w:tblPr>).)*" + re.escape(CENTRE), document, flags=re.S)),
        "centred_captions": document.count(CAPTION_STYLE + CENTRE),
        "cells": len(re.findall(r"<w:tc>", document)),
        "bordered_cells": document.count("<w:tc>" + CELL_BORDERS),
        "rows": len(re.findall(r"<w:tr>", document)),
        "unsplittable_rows": document.count("<w:tr><w:trPr><w:cantSplit/></w:trPr>"),
        "bold_header_runs": sum(re.search(r"<w:tr>.*?</w:tr>", t, re.S).group(0).count("<w:rPr><w:b/>")
                                for t in re.findall(r"<w:tbl>.*?</w:tbl>", document, re.S)),
        "images": len(media),
        "gifs": sum(n.lower().endswith(".gif") for n in media),
        "tex_left": len(re.findall(re.escape(B) + r"(?:vec|frac|partial|times|hat)\b", text_only)),
        "author": author.group(1) if author else "",
    }
