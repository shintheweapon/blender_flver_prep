"""
The fonts and styles of the Word file, after pandoc: the East Asian font and
language, and upright table captions.
"""

import re


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
