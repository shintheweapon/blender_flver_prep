"""
The Word package's XML, after pandoc: the page number in the footer and the
page's size and margins, upright numbers in maths, figures centred and kept
with their captions, the rewrite of parts inside the ``.docx`` file, and the check of
what the file holds. The tables are in ``docx_tables.py``, the fonts and
styles in ``docx_styles.py``. ``export_docx.py`` prepares the paper and its
figures and calls these.
"""

import io
import re
import zipfile

from docx_tables import CAPTION_STYLE, CENTRE, column_bounds, cell_lines, table_cells

B = "\\"


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


PAGE_SIZE = '<w:pgSz w:w="12240" w:h="15840"/>'  # US Letter, as IEEE uses


def set_page(document_xml, margin):
    """
    Give the document's last section a page size (``PAGE_SIZE``) and margins.

    Parameters
    ----------
    document_xml : str
    margin : int
        Twips on every side; the header and footer sit at half an inch.

    Returns
    -------
    str
        Unchanged when the section already has a page size.
    """
    if "<w:pgSz" in document_xml:
        return document_xml
    page = (PAGE_SIZE + f'<w:pgMar w:top="{margin}" w:right="{margin}" w:bottom="{margin}" w:left="{margin}" '
            'w:header="720" w:footer="720" w:gutter="0"/>')
    body_end = document_xml.rindex("</w:body>")
    body, rest = document_xml[:body_end], document_xml[body_end:]
    found = list(re.finditer(r"<w:sectPr\b[^>]*>", body))
    if not found:
        return body + f"<w:sectPr>{page}</w:sectPr>" + rest
    tag = found[-1]
    if tag.group(0).endswith("/>"):
        return body[:tag.start()] + tag.group(0)[:-2].rstrip() + ">" + page + "</w:sectPr>" + body[tag.end():] + rest
    close = body.index("</w:sectPr>", tag.end())
    return body[:close] + page + body[close:] + rest


PARAGRAPH = re.compile(r"<w:p>(?:(?!</w:p>).)*</w:p>", re.S)
DRAWING = re.compile(r"<w:drawing>.*?</w:drawing>", re.S)
# The maths pictures of ``math_images``, by the file name pandoc writes into the picture
MATH_PICTURE = re.compile(r'descr="(?:math/)?math_[id]_[0-9a-f]{12}\.png"')


def holds_figure(paragraph_xml):
    """
    Whether a paragraph holds a figure: a picture other than a maths picture.

    Parameters
    ----------
    paragraph_xml : str

    Returns
    -------
    bool
    """
    return any(not MATH_PICTURE.search(drawing) for drawing in DRAWING.findall(paragraph_xml))


def keep_figures_with_captions(document_xml):
    """
    Keep each figure on the same page as the paragraph after it, its caption
    (or, for Fig. 3(a), Fig. 3(b) and then the caption): every paragraph holding
    a figure (``holds_figure``) gets ``<w:keepNext/>``.

    Parameters
    ----------
    document_xml : str

    Returns
    -------
    str
    """
    def paragraph(match):
        xml = match.group(0)
        if not holds_figure(xml) or "<w:keepNext" in xml:
            return xml
        if xml.startswith("<w:p><w:pPr>"):
            style = re.match(r"<w:p><w:pPr>(<w:pStyle\b[^>]*/>)?", xml)
            return xml[:style.end()] + "<w:keepNext/>" + xml[style.end():]
        return "<w:p><w:pPr><w:keepNext/></w:pPr>" + xml[len("<w:p>"):]

    return PARAGRAPH.sub(paragraph, document_xml)


def centre_figures(document_xml):
    """
    Centre every figure on the page: each paragraph holding a figure
    (``holds_figure``) gets ``<w:jc w:val="center"/>``, last in its paragraph
    properties as the schema orders them. Paragraphs that already set an
    alignment are left.

    Parameters
    ----------
    document_xml : str

    Returns
    -------
    str
    """
    def paragraph(match):
        xml = match.group(0)
        if not holds_figure(xml) or "<w:jc " in xml:
            return xml
        if xml.startswith("<w:p><w:pPr>"):
            end = xml.index("</w:pPr>")
            mark = xml.find("<w:rPr>", 0, end)  # the paragraph mark's run properties come after jc
            at = end if mark < 0 else mark
            return xml[:at] + CENTRE + xml[at:]
        return "<w:p><w:pPr>" + CENTRE + "</w:pPr>" + xml[len("<w:p>"):]

    return PARAGRAPH.sub(paragraph, document_xml)


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


def squeezed(table_xml):
    """
    Whether a table has a column narrower than its widest unbreakable piece
    (``docx_tables.column_bounds``), so a word in it would break.

    Parameters
    ----------
    table_xml : str

    Returns
    -------
    bool
    """
    grid = [int(w) for w in re.findall(r'<w:gridCol w:w="(\d+)"', table_xml)]
    minimums, _ = column_bounds([[cell_lines(cell) for cell in row] for row in table_cells(table_xml)])
    return not grid or any(width < minimum for width, minimum in zip(grid, minimums))


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
        referenced); ``page_margin``, ``fixed_tables``, ``squeezed_tables``
        (tables with a column narrower than a word in it),
        ``figures_kept_with_captions``, ``centred_figures`` and ``latin_font``;
        ``math_pictures`` and ``numbered_equations`` (maths drawn as pictures,
        and display equations with their number at the right margin);
        ``italic_number_runs`` (numbers in maths left italic), ``italic_cjk_runs`` (italic runs of Chinese text) and ``italic_captions``
        (whether table captions are still italic).
    """
    with zipfile.ZipFile(path) as package:
        document = package.read("word/document.xml").decode("utf-8")
        media = [n for n in package.namelist() if n.startswith("word/media/")]
        core = package.read("docProps/core.xml").decode("utf-8")
        styles = package.read("word/styles.xml").decode("utf-8")
        footer = package.read(FOOTER_PART).decode("utf-8") if FOOTER_PART in package.namelist() else ""
    # the visible text: maths and picture descriptions (a maths picture's TeX) left out
    text_only = "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>",
                                   re.sub(r"<m:oMath.*?</m:oMath>", "", document, flags=re.S)))
    defaults = (re.findall(r"<w:docDefaults>.*?</w:docDefaults>", styles, flags=re.S) + [""])[0]
    author = re.search(r"<dc:creator>(.*?)</dc:creator>", core)
    return {
        "equations": len(re.findall(r"<m:oMath[ >]", document)),
        "tables": document.count("<w:tbl>"),
        "bordered_tables": len(re.findall(r"<w:tblPr>(?:(?!</w:tblPr>).)*<w:tblBorders>", document, flags=re.S)),
        "centred_tables": len(re.findall(r"<w:tblPr>(?:(?!</w:tblPr>).)*" + re.escape(CENTRE), document, flags=re.S)),
        "centred_captions": document.count(CAPTION_STYLE + CENTRE),
        "cells": len(re.findall(r"<w:tc>", document)),
        "bordered_cells": len(re.findall(r"<w:tc><w:tcPr>(?:<w:tcW\b[^>]*/>)?<w:tcBorders>", document)),
        "rows": len(re.findall(r"<w:tr>", document)),
        "unsplittable_rows": document.count("<w:tr><w:trPr><w:cantSplit/></w:trPr>"),
        "bold_header_runs": sum(len(re.findall(r"<w:rPr>(?:<w:rFonts\b[^>]*/>)?<w:b/>",
                                               re.search(r"<w:tr>.*?</w:tr>", t, re.S).group(0)))
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
        "page_margin": int((re.findall(r'<w:pgMar w:top="(\d+)"', document) + ["0"])[0]),
        "fixed_tables": document.count('<w:tblLayout w:type="fixed"/>'),
        "squeezed_tables": sum(1 for table in re.findall(r"<w:tbl>.*?</w:tbl>", document, re.S)
                               if squeezed(table)),
        "figures_kept_with_captions": sum(1 for p in PARAGRAPH.findall(document)
                                          if holds_figure(p) and "<w:keepNext" in p),
        "centred_figures": sum(1 for p in PARAGRAPH.findall(document) if holds_figure(p) and CENTRE in p),
        "math_pictures": sum(1 for d in DRAWING.findall(document) if MATH_PICTURE.search(d)),
        "numbered_equations": len(re.findall(r'<w:tab w:val="right"[^>]*/></w:tabs>(?:(?!</w:p>).)*'
                                             r'<w:r><w:tab/><w:t>\(\d+\)</w:t></w:r></w:p>', document, flags=re.S)),
        "latin_font": (re.findall(r'<w:rFonts\b[^>]*\bw:ascii="([^"]*)"', defaults) + ["theme"])[0],
        "italic_captions": not re.search(r'w:styleId="TableCaption"(?:(?!</w:style>).)*<w:i w:val="0"',
                                         styles, flags=re.S),
    }
