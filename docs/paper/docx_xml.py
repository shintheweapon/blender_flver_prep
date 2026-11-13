"""
The Word package's XML, after pandoc: the tables' borders, centring and
unsplittable rows, the page number in the footer, the East Asian font and
language, the rewrite of parts inside the ``.docx`` file, and the check of what
the file holds. ``export_docx.py`` prepares the paper and its
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


def rewrite_package(path, changes, added=None):
    """
    Rewrite parts of a Word file, and add new ones, keeping every other part
    as it is and in the same order.

    Parameters
    ----------
    path : str
    changes : dict
        Part name (``word/document.xml``) to a function that takes and
        returns that part's text.
    added : dict or None
        New part names to their bytes, written after the existing parts; a part
        that already exists is replaced in place instead.
    """
    added = dict(added or {})
    with zipfile.ZipFile(path) as package:
        parts = [(info, package.read(info.filename)) for info in package.infolist()]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as package:
        for info, data in parts:
            if info.filename in added:
                data = added.pop(info.filename)
            elif info.filename in changes:
                data = changes[info.filename](data.decode("utf-8")).encode("utf-8")
            package.writestr(info, data)
        for name, data in added.items():
            package.writestr(name, data)
    with open(path, "wb") as file:
        file.write(buffer.getvalue())


def rewrite_document(path, change):
    """
    Apply ``change`` to ``word/document.xml`` inside a Word file (``rewrite_package``).

    Parameters
    ----------
    path : str
    change : callable
        Takes and returns the document XML as text.
    """
    rewrite_package(path, {"word/document.xml": change})


FOOTER_PART = "word/footer1.xml"
FOOTER_ID = "rIdPageNumbers"
FOOTER_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer"
FOOTER_CONTENT = "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def footer_xml():
    """
    A footer part holding the page number, centred: one paragraph with a
    ``PAGE`` field.

    Returns
    -------
    str
    """
    run = '<w:r><w:fldChar w:fldCharType="{}"/></w:r>'
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:ftr xmlns:w="{W_NS}" xmlns:r="{R_NS}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
            + run.format("begin") + '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
            + run.format("separate") + "<w:r><w:t>1</w:t></w:r>" + run.format("end") + "</w:p></w:ftr>")


def add_footer(document_xml, rid=FOOTER_ID):
    """
    Point the document's last section at a footer, by relationship ID.

    The reference goes first in the body's last ``<w:sectPr>``, which pandoc
    writes empty (``<w:sectPr />``), or in a new one where there is none; a
    document that already refers to ``rid`` is returned unchanged.

    Parameters
    ----------
    document_xml : str
    rid : str

    Returns
    -------
    str
    """
    if f'r:id="{rid}"' in document_xml:
        return document_xml
    reference = f'<w:footerReference w:type="default" r:id="{rid}"/>'
    body_end = document_xml.rindex("</w:body>")
    body, rest = document_xml[:body_end], document_xml[body_end:]
    found = list(re.finditer(r"<w:sectPr\b[^>]*>", body))
    if not found:
        return body + f"<w:sectPr>{reference}</w:sectPr>" + rest
    tag = found[-1]
    if tag.group(0).endswith("/>"):
        opening = tag.group(0)[:-2].rstrip() + ">"
        return body[:tag.start()] + opening + reference + "</w:sectPr>" + body[tag.end():] + rest
    return body[:tag.end()] + reference + body[tag.end():] + rest


def add_relationship(rels_xml, rid, kind, target):
    """
    Add a relationship to a ``.rels`` part, unless one with that ID exists.

    Parameters
    ----------
    rels_xml : str
    rid, kind, target : str
        The relationship's ID, type URI and target part (relative).

    Returns
    -------
    str
    """
    if f'Id="{rid}"' in rels_xml:
        return rels_xml
    entry = f'<Relationship Type="{kind}" Id="{rid}" Target="{target}" />'
    return rels_xml.replace("</Relationships>", entry + "</Relationships>")


def add_override(types_xml, part, content_type):
    """
    Declare a part's content type in ``[Content_Types].xml``, unless it is declared.

    Parameters
    ----------
    types_xml : str
    part : str
        The part name, as ``word/footer1.xml``.
    content_type : str

    Returns
    -------
    str
    """
    name = "/" + part.lstrip("/")
    if f'PartName="{name}"' in types_xml:
        return types_xml
    entry = f'<Override PartName="{name}" ContentType="{content_type}" />'
    return types_xml.replace("</Types>", entry + "</Types>")


def set_east_asian_font(styles_xml, font, lang):
    """
    Give East Asian text a font and language in ``word/styles.xml``.

    Every ``w:eastAsiaTheme`` attribute, which takes the font from the theme,
    gives way to ``w:eastAsia`` with ``font``; the default language
    (``w:docDefaults``) becomes ``lang`` for its main and its East Asian text.
    Latin fonts are left as they are.

    Parameters
    ----------
    styles_xml : str
    font : str
    lang : str
        A language tag, as ``zh-CN``.

    Returns
    -------
    str
    """
    def fonts(match):
        tag = re.sub(r'\s*w:eastAsiaTheme="[^"]*"', "", match.group(0))
        if "w:eastAsia=" in tag:
            return re.sub(r'w:eastAsia="[^"]*"', f'w:eastAsia="{font}"', tag)
        return tag.replace("<w:rFonts", f'<w:rFonts w:eastAsia="{font}"', 1)

    styles_xml = re.sub(r"<w:rFonts\b[^>]*>", fonts, styles_xml)

    def defaults(match):
        block = match.group(0)
        new = f'<w:lang w:bidi="ar-SA" w:eastAsia="{lang}" w:val="{lang}" />'
        found = re.search(r"<w:lang\b[^>]*/>", block)
        if found:
            return block.replace(found.group(0), new, 1)
        return block.replace("</w:rPr>", new + "</w:rPr>", 1)

    return re.sub(r"<w:docDefaults>.*?</w:docDefaults>", defaults, styles_xml, count=1, flags=re.S)


NUMBER = re.compile(r"[0-9]+(?:[.,][0-9]+)*")
MATH_RUN = re.compile(r"<m:r>(?:(?!</m:r>).)*</m:r>", re.S)


def upright_numbers(document_xml):
    """
    Set every number inside maths upright, as numbers are by convention.

    pandoc marks maths operators plain (``<m:sty m:val="p"/>``) but leaves
    numbers, equation numbers among them, to the maths italic. Each maths run
    whose text is a number gets ``m:sty p``; variables and runs already plain
    are left as they are.

    Parameters
    ----------
    document_xml : str

    Returns
    -------
    str
    """
    def run(match):
        xml = match.group(0)
        text = re.search(r"<m:t[^>]*>([^<]*)</m:t>", xml)
        if not text or not NUMBER.fullmatch(text.group(1)) or "<m:sty " in xml or "<m:nor" in xml:
            return xml
        if "<m:rPr>" in xml:
            return xml.replace("<m:rPr>", '<m:rPr><m:sty m:val="p" />', 1)
        return xml.replace("<m:r>", '<m:r><m:rPr><m:sty m:val="p" /></m:rPr>', 1)

    return MATH_RUN.sub(run, document_xml)


def set_caption_style(styles_xml, small_caps):
    """
    Set table captions upright, as IEEE style does, and in small capitals when asked.

    pandoc's ``TableCaption`` style is based on ``Caption``, which is italic; the
    style gains run properties that switch the italic off (``<w:i w:val="0"/>``)
    and, with ``small_caps``, turn small capitals on. They go after the style's
    paragraph properties, in schema order.

    Parameters
    ----------
    styles_xml : str
    small_caps : bool
        True for English captions; small capitals do nothing to Chinese.

    Returns
    -------
    str
    """
    def style(match):
        xml = re.sub(r"<w:rPr>.*?</w:rPr>", "", match.group(0), flags=re.S)
        props = '<w:rPr><w:i w:val="0" />' + ("<w:smallCaps />" if small_caps else "") + "</w:rPr>"
        return xml.replace("</w:style>", props + "</w:style>")

    return re.sub(r'<w:style\b[^>]*w:styleId="TableCaption".*?</w:style>', style, styles_xml, count=1, flags=re.S)


def finish(path, document, styles=None):
    """
    The edits after pandoc, in one rewrite of the Word file: the document's
    and the styles' own edits, and a centred page number in the footer.

    Parameters
    ----------
    path : str
    document : callable
        Takes and returns the document XML (``format_tables``, ``upright_numbers``).
    styles : callable or None
        Takes and returns the styles XML (``set_caption_style``,
        ``set_east_asian_font``); None leaves the styles.
    """
    changes = {
        "word/document.xml": lambda xml: add_footer(document(xml)),
        "word/_rels/document.xml.rels": lambda xml: add_relationship(xml, FOOTER_ID, FOOTER_TYPE, "footer1.xml"),
        "[Content_Types].xml": lambda xml: add_override(xml, FOOTER_PART, FOOTER_CONTENT),
    }
    if styles:
        changes["word/styles.xml"] = styles
    rewrite_package(path, changes, {FOOTER_PART: footer_xml().encode("utf-8")})


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
        author field); ``east_asian_font`` and ``language`` (the styles'
        defaults); ``page_numbers`` (whether the footer with the page number is
        referenced); ``italic_number_runs`` (numbers in maths left italic),
        ``italic_cjk_runs`` (italic runs of Chinese text) and ``italic_captions``
        (whether table captions are still italic).
    """
    with zipfile.ZipFile(path) as package:
        document = package.read("word/document.xml").decode("utf-8")
        media = [n for n in package.namelist() if n.startswith("word/media/")]
        core = package.read("docProps/core.xml").decode("utf-8")
        styles = package.read("word/styles.xml").decode("utf-8")
        footer = package.read(FOOTER_PART).decode("utf-8") if FOOTER_PART in package.namelist() else ""
    text_only = re.sub(r"<m:oMath.*?</m:oMath>", "", document, flags=re.S)
    defaults = (re.findall(r"<w:docDefaults>.*?</w:docDefaults>", styles, flags=re.S) + [""])[0]
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
        "east_asian_font": (re.findall(r'<w:rFonts\b[^>]*\bw:eastAsia="([^"]*)"', defaults) + [""])[0],
        "language": (re.findall(r'<w:lang\b[^>]*\bw:val="([^"]*)"', defaults) + [""])[0],
        "page_numbers": f'r:id="{FOOTER_ID}"' in document and " PAGE " in footer,
        "italic_number_runs": sum(1 for run in MATH_RUN.findall(document)
                                  if re.search(r"<m:t[^>]*>[0-9]+(?:[.,][0-9]+)*</m:t>", run)
                                  and "<m:sty " not in run and "<m:nor" not in run),
        "italic_cjk_runs": len(re.findall(r"<w:r>(?:(?!</w:r>).)*<w:i ?/>(?:(?!</w:r>).)*<w:t[^>]*>[^<]*"
                                          r"[\u4e00-\u9fff]", document, flags=re.S)),
        "italic_captions": not re.search(r'w:styleId="TableCaption"(?:(?!</w:style>).)*<w:i w:val="0"',
                                         styles, flags=re.S),
    }
