"""
The tables of the Word file, after pandoc: their borders, centring and
unsplittable rows, their bold header, their columns sized to their content,
and line breaks before a first-column cell's bracketed part.
"""

import re
import unicodedata

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


# Estimated widths at 12 pt, in twips: a Latin character and a Chinese one; text is counted TEXT_SLACK wider, and
# bold header text HEADER_FACTOR wider again, since wide letters (M, W) and rounding would otherwise break a word
LATIN_TWIPS = 120
WIDE_TWIPS = 240
TEXT_SLACK = 1.08
HEADER_FACTOR = 1.1
# Each cell's left and right margin (0.05 in, tighter than Word's 0.075 in), and the room a column keeps beyond its
# text: both margins and 60 twips for the borders and rounding
CELL_MARGIN = 72
CELL_PADDING = 2 * CELL_MARGIN + 60
CELL_MARGINS = (f'<w:tblCellMar><w:left w:w="{CELL_MARGIN}" w:type="dxa"/>'
                f'<w:right w:w="{CELL_MARGIN}" w:type="dxa"/></w:tblCellMar>')
# Chinese may break between any two characters; a column still keeps this many of them together
WIDE_KEEP = 4
WIDE_CHARS = r"　-〿㐀-鿿豈-﫿＀-￯"
PIECE = re.compile(rf"[{WIDE_CHARS}]+|[^\s{WIDE_CHARS}]+")


def text_twips(text):
    """
    Estimated width of text on one line, in twips.

    Parameters
    ----------
    text : str

    Returns
    -------
    int
    """
    return sum(WIDE_TWIPS if unicodedata.east_asian_width(c) in "WF" else LATIN_TWIPS for c in text)


def pieces(line):
    """
    The parts of a line that cannot break: runs of Latin letters, digits and
    their punctuation (``“cloth”``), and runs of Chinese cut to ``WIDE_KEEP``
    characters.

    Parameters
    ----------
    line : str

    Returns
    -------
    list of str
    """
    found = []
    for run in PIECE.findall(line):
        if re.match(rf"[{WIDE_CHARS}]", run):
            found += [run[i:i + WIDE_KEEP] for i in range(0, len(run), WIDE_KEEP)]
        else:
            found.append(run)
    return found


def column_bounds(rows):
    """
    Each column's minimum and preferred width, in twips, padding included.

    The minimum is the column's widest unbreakable piece (``pieces``); the
    preferred width is its longest line. Text counts ``TEXT_SLACK`` wider, and
    header text (the first row) ``HEADER_FACTOR`` wider again, as it is bold.

    Parameters
    ----------
    rows : list of list of list of str
        Per row, per cell, the cell's lines.

    Returns
    -------
    tuple
        ``(minimums, preferred)``, lists of int.
    """
    columns = max(len(row) for row in rows)
    minimums, preferred = [CELL_PADDING] * columns, [CELL_PADDING] * columns
    for index, row in enumerate(rows):
        factor = TEXT_SLACK * (HEADER_FACTOR if index == 0 else 1.0)
        for column, lines in enumerate(row):
            for line in lines:
                widest = max((text_twips(piece) for piece in pieces(line)), default=0)
                minimums[column] = max(minimums[column], int(round(widest * factor)) + CELL_PADDING)
                preferred[column] = max(preferred[column], int(round(text_twips(line) * factor)) + CELL_PADDING)
    return minimums, preferred


def column_widths(rows, available):
    """
    The width of each column, in twips, within ``available``.

    The preferred widths are used when they fit. Otherwise each column gets
    its minimum and a share of the rest in proportion to how much more it would
    like, up to its preferred width; minimums that do not fit at all are
    scaled down to fit.

    Parameters
    ----------
    rows : list of list of list of str
        Per row, per cell, the cell's lines.
    available : int
        Twips.

    Returns
    -------
    tuple
        ``(widths, squeezed)``: a list of int, and whether the minimums had to
        be scaled down.
    """
    minimums, preferred = column_bounds(rows)
    if sum(preferred) <= available:
        return preferred, False
    if sum(minimums) >= available:
        return [int(m * available / sum(minimums)) for m in minimums], sum(minimums) > available
    wants = [p - m for m, p in zip(minimums, preferred)]
    spare = available - sum(minimums)
    return [m + int(spare * w / sum(wants)) for m, w in zip(minimums, wants)], False


def cell_lines(cell_xml):
    """
    The lines of a table cell's text: one per paragraph, split again at line breaks.

    Parameters
    ----------
    cell_xml : str

    Returns
    -------
    list of str
    """
    lines = []
    for paragraph in re.findall(r"<w:p\b.*?</w:p>", cell_xml, re.S):
        for part in re.split(r"<w:br\s*/>", paragraph):
            lines.append("".join(re.findall(r"<(?:w|m):t(?:\s[^>]*)?>([^<]*)</(?:w|m):t>", part)))
    return lines


def table_cells(table_xml):
    """
    A table's cells, per row, as their XML.

    Parameters
    ----------
    table_xml : str

    Returns
    -------
    list of list of str
    """
    return [re.findall(r"<w:tc>.*?</w:tc>", row, re.S) for row in re.findall(r"<w:tr>.*?</w:tr>", table_xml, re.S)]


def set_table_widths(document_xml, available):
    """
    Give every table columns sized to its content (``column_widths``).

    Each table gets the computed ``<w:tblGrid>``, a ``<w:tcW>`` in every cell,
    its total as ``<w:tblW>``, a fixed layout (``<w:tblLayout>``), so Word,
    LibreOffice and Google Docs all keep the widths, and cell margins of
    ``CELL_MARGIN`` (``<w:tblCellMar>``). Running it again gives the same result.

    Parameters
    ----------
    document_xml : str
    available : int
        The text width, in twips.

    Returns
    -------
    str
    """
    def table(match):
        xml = match.group(0)
        cells = table_cells(xml)
        widths, _ = column_widths([[cell_lines(cell) for cell in row] for row in cells], available)

        def properties(found):
            parts = dict(child_elements(found.group(1)))
            parts["tblW"] = f'<w:tblW w:type="dxa" w:w="{sum(widths)}"/>'
            parts["tblLayout"] = '<w:tblLayout w:type="fixed"/>'
            parts["tblCellMar"] = CELL_MARGINS
            return "<w:tblPr>" + "".join(parts[n] for n in TABLE_PROPERTY_ORDER if parts.get(n)) + "</w:tblPr>"

        xml = TABLE_PROPERTIES.sub(properties, xml, count=1)
        grid = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>"
        if "<w:tblGrid>" in xml:
            xml = re.sub(r"<w:tblGrid>.*?</w:tblGrid>", grid, xml, count=1, flags=re.S)
        else:
            xml = xml.replace("</w:tblPr>", "</w:tblPr>" + grid, 1)

        def row(found):
            column = iter(widths)

            def cell(found_cell):
                body = re.sub(r"<w:tcW\b[^>]*/>", "", found_cell.group(1))
                width = f'<w:tcW w:type="dxa" w:w="{next(column, widths[-1])}"/>'
                if body.startswith("<w:tcPr>"):
                    body = "<w:tcPr>" + width + body[len("<w:tcPr>"):]
                else:
                    body = "<w:tcPr>" + width + "</w:tcPr>" + body
                return "<w:tc>" + body + "</w:tc>"

            return re.sub(r"<w:tc>(.*?)</w:tc>", cell, found.group(0), flags=re.S)

        return re.sub(r"<w:tr>.*?</w:tr>", row, xml, flags=re.S)

    return re.sub(r"<w:tbl>.*?</w:tbl>", table, document_xml, flags=re.S)


def break_before_brackets(document_xml):
    """
    Put a first-column cell's bracketed part on its own line, as in
    ``WP`` / ``（武器）``: a ``<w:br/>`` before the ``（`` of a cell whose text is
    a name followed by a part in full-width brackets. Other cells, and cells
    that already break, are left as they are.

    Parameters
    ----------
    document_xml : str

    Returns
    -------
    str
    """
    def row(found):
        cells = list(re.finditer(r"<w:tc>.*?</w:tc>", found.group(0), re.S))
        if not cells:
            return found.group(0)
        first = cells[0].group(0)
        text = "".join(cell_lines(first))
        if "<w:br" in first or not re.fullmatch(r"[^（）]+（[^（）]+）", text):
            return found.group(0)
        if re.search(r"<w:t(?:\s[^>]*)?>（", first):
            changed = re.sub(r"(<w:t(?:\s[^>]*)?>（)", r"<w:br/>\1", first, count=1)
        else:
            changed = re.sub(r"(<w:t(?:\s[^>]*)?>)([^<（]+)（", r'\1\2</w:t><w:br/><w:t xml:space="preserve">（',
                             first, count=1)
        start, end = cells[0].span()
        return found.group(0)[:start] + changed + found.group(0)[end:]

    return re.sub(r"<w:tr>.*?</w:tr>", row, document_xml, flags=re.S)
