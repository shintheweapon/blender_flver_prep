"""
The fonts and styles of the Word file, after pandoc: the East Asian font and
language, upright table captions, and the serif edition's serif body with
sans headings, table headers and figure captions.
"""

import re

from docx_xml import PARAGRAPH


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


SERIF = ("Noto Serif", "Noto Serif SC")
SANS = ("Noto Sans", "Noto Sans SC")
SANS_STYLES = ("Title",) + tuple(f"Heading{n}" for n in range(1, 10)) + ("TableCaption",)


def fonts_tag(latin, east_asian):
    """A ``<w:rFonts>`` naming a Latin and an East Asian font."""
    return f'<w:rFonts w:ascii="{latin}" w:eastAsia="{east_asian}" w:hAnsi="{latin}" w:cstheme="minorBidi" />'


def set_serif_body(styles_xml):
    """
    The serif edition's styles: body text in ``SERIF``, headings and table
    captions (``SANS_STYLES``) in ``SANS``.

    The default run fonts lose their theme fonts for Noto Serif and Noto Serif
    SC; each style in ``SANS_STYLES`` gets Noto Sans and Noto Sans SC, first in
    its run properties. Running it again changes nothing.

    Parameters
    ----------
    styles_xml : str

    Returns
    -------
    str
    """
    def defaults(match):
        return re.sub(r"<w:rFonts\b[^>]*/>", fonts_tag(*SERIF), match.group(0), count=1)

    styles_xml = re.sub(r"<w:docDefaults>.*?</w:docDefaults>", defaults, styles_xml, count=1, flags=re.S)
    for style_id in SANS_STYLES:
        def style(match):
            xml = re.sub(r"<w:rFonts\b[^>]*/>", "", match.group(0))
            if "<w:rPr>" in xml:
                return xml.replace("<w:rPr>", "<w:rPr>" + fonts_tag(*SANS), 1)
            return xml.replace("</w:style>", "<w:rPr>" + fonts_tag(*SANS) + "</w:rPr></w:style>")

        styles_xml = re.sub(rf'<w:style\b[^>]*w:styleId="{style_id}".*?</w:style>', style, styles_xml, count=1,
                            flags=re.S)
    return styles_xml


def sans_runs(document_xml, caption_pattern):
    """
    Set table header rows and figure captions in ``SANS`` in the serif edition.

    Every text run (``<w:r>``) in a table's first row, and in a paragraph whose
    text starts with ``caption_pattern``, gets Noto Sans and Noto Sans SC,
    after any run style, as the schema orders them. Runs that already name
    their fonts are left as they are.

    Parameters
    ----------
    document_xml : str
    caption_pattern : str
        A regular expression for the start of a caption, as ``图 \\d+\\.``.

    Returns
    -------
    str
    """
    def runs(xml):
        def run(match):
            body = match.group(1)
            if "<w:rFonts" in body:
                return match.group(0)
            if body.startswith("<w:rPr>"):
                style = re.match(r"<w:rPr>(<w:rStyle\b[^>]*/>)?", body)
                body = body[:style.end()] + fonts_tag(*SANS) + body[style.end():]
            else:
                body = "<w:rPr>" + fonts_tag(*SANS) + "</w:rPr>" + body
            return "<w:r>" + body + "</w:r>"

        return re.sub(r"<w:r>(.*?)</w:r>", run, xml, flags=re.S)

    def table(match):
        first = re.search(r"<w:tr>.*?</w:tr>", match.group(0), re.S)
        return match.group(0)[:first.start()] + runs(first.group(0)) + match.group(0)[first.end():]

    document_xml = re.sub(r"<w:tbl>.*?</w:tbl>", table, document_xml, flags=re.S)

    def paragraph(match):
        text = "".join(re.findall(r"<w:t(?:\s[^>]*)?>([^<]*)</w:t>", match.group(0)))
        return runs(match.group(0)) if re.match(caption_pattern, text) else match.group(0)

    return PARAGRAPH.sub(paragraph, document_xml)
