"""
Export the paper to a Word file for Google Docs: native equations, the
figures as images, the tables with their captions.

Run ``python docs/paper/export_docx.py``. It writes
``docs/paper/out/ER_NORMAL_MAPS.docx`` and the images it embeds (git-ignored).
Upload the ``.docx`` to Google Drive and open it with Google Docs, which turns
the Word equations into its own.

The still figures become PNGs at twice their size, captured with headless
Chrome on a white page in light mode; the animated ones (Figs. 3(a) and 7)
become animated GIFs, as Google Docs plays GIFs but not animated SVG; the
screenshots become PNGs. Needs pandoc and ffmpeg, and, for the figures,
Chrome and the ``websocket-client`` package. The edits to the Word file's XML
(tables, the check of what it holds) are in ``docx_xml.py``.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile

PAPER_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.dirname(PAPER_DIR)
PAPER = os.path.join(PAPER_DIR, "ER_NORMAL_MAPS.md")
OUT_DIR = os.path.join(PAPER_DIR, "out")
VIDEO_DIR = os.path.join(DOCS_DIR, "video")
if VIDEO_DIR not in sys.path:
    sys.path.insert(0, VIDEO_DIR)

import languages  # noqa: E402  (the paper of each language)
import scenes  # noqa: E402  (scenes.moves tells the animated figures apart; it imports no browser code)
from docx_tables import (BORDER_EDGES, CAPTION_STYLE, CELL_BORDERS, CENTRE, TABLE_BORDERS,  # noqa: E402,F401
                         TABLE_PROPERTIES, TABLE_PROPERTY_ORDER, break_before_brackets, child_elements,
                         format_tables, set_table_widths, table_properties, table_rows)
from docx_styles import set_caption_style, set_east_asian_font  # noqa: E402
from docx_xml import (centre_figures, check_docx, finish, keep_figures_with_captions,  # noqa: E402,F401
                      rewrite_document, set_page, upright_numbers)

STILL_SCALE = 2.0
GIF_SCALE = 1.5
GIF_TIMING = {"paper_axis_swap_animated.svg": (10, 30.0), "paper_dome_tilts.svg": (15, 5.0)}
MAX_WIDTH_INCHES = 6.5
# No figure taller than this, so it and its caption fit on a page between 0.75 in margins
MAX_HEIGHT_INCHES = 7.0
MARGIN = 1080  # twips, 0.75 in
TEXT_WIDTH = 12240 - 2 * MARGIN  # US Letter less two margins, in twips
PANDOC_FORMAT = "markdown-implicit_figures"
B = "\\"
TAG = re.compile(re.escape(B + "tag{") + r"([^}]*)\}")
TABLE_CAPTION = re.compile(r'<p align="center">(?:TABLE|表) ([IVXL]+)<br>(.*?)</p>')
# The line under the title that links the paper in the other language, a dead link in a Word file
LANGUAGE_LINE = re.compile(r"\]\(ER_NORMAL_MAPS[\w.-]*\.md\)")
# The font of Chinese text in the Chinese Word file: Source Han Sans SC under the name Google Docs offers
EAST_ASIAN = {"zh-CN": ("Noto Sans SC", "zh-CN")}
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def images(text):
    """
    The paper's images, in order.

    Parameters
    ----------
    text : str
        The paper's Markdown.

    Returns
    -------
    list of str
        Each image's path as written in the paper (relative to ``docs/paper``).
    """
    return [match.group(2) for match in IMAGE.finditer(text)]


def export_name(source):
    """
    The file an image becomes: a GIF for an animated figure, a PNG otherwise.

    Parameters
    ----------
    source : str
        The image's path as written in the paper.

    Returns
    -------
    str
    """
    stem, extension = os.path.splitext(os.path.basename(source))
    if extension.lower() == ".svg" and scenes.moves(("figure", os.path.basename(source))):
        return stem + ".gif"
    return stem + ".png"


def prepare_markdown(text, widths=None):
    """
    The paper's Markdown, rewritten for pandoc's Word output.

    - ``\\tag{n}`` becomes ``\\qquad (n)``, which pandoc can turn into a Word
      equation;
    - each ``<p align="center">TABLE N<br>CAPTION</p>`` becomes a pandoc table
      caption, ``Table: TABLE N. CAPTION``, which Word places above the table
      (``表 N<br>`` becomes ``Table: 表 N　CAPTION``);
    - the language line under the title, which links the other paper's
      Markdown file, is left out;
    - each image points at its exported file, with its width in inches.

    Parameters
    ----------
    text : str
    widths : dict or None
        Exported file name to width in inches; images not in it get no width.

    Returns
    -------
    str
    """
    widths = widths or {}
    text = TAG.sub(lambda m: f"{B}qquad ({m.group(1)})", text)
    text = TABLE_CAPTION.sub(lambda m: (f"Table: 表 {m.group(1)}　{m.group(2)}"
                                        if m.group(0).startswith('<p align="center">表')
                                        else f"Table: TABLE {m.group(1)}. {m.group(2)}"), text)
    text = drop_language_line(text)

    def image(match):
        name = export_name(match.group(2))
        size = f"{{width={widths[name]:.2f}in}}" if name in widths else ""
        return f"![{match.group(1)}]({name}){size}"

    return IMAGE.sub(image, text)


def drop_language_line(text):
    """
    The paper without its language line: the first line, among the first five,
    that links one of the papers' Markdown files, and the blank line after it.

    Parameters
    ----------
    text : str

    Returns
    -------
    str
    """
    lines = text.split("\n")
    for index, line in enumerate(lines[:5]):
        if LANGUAGE_LINE.search(line):
            drop = 2 if index + 1 < len(lines) and not lines[index + 1].strip() else 1
            return "\n".join(lines[:index] + lines[index + drop:])
    return text


def gif_timing(source):
    """
    Frames a second and seconds of an animated figure's GIF, by its English
    name (``.zh.svg`` is read as ``.svg``).

    Raises
    ------
    KeyError
        For a figure that is not animated.
    """
    return GIF_TIMING[os.path.basename(source).replace(".zh.svg", ".svg")]


def figure_width(width, height):
    """
    The width in inches a figure is shown at: its own size at 96 pixels an
    inch, no wider than ``MAX_WIDTH_INCHES`` and no taller than
    ``MAX_HEIGHT_INCHES``, keeping its shape.

    Parameters
    ----------
    width, height : float
        The figure's size in pixels.

    Returns
    -------
    float
    """
    return min(width / 96.0, MAX_WIDTH_INCHES, MAX_HEIGHT_INCHES * width / height)


def figure_size(target, svg=None):
    """The size of a figure in pixels: its SVG's declared size, or the exported image's."""
    if svg is not None:
        return svg_size(svg)
    from PIL import Image
    with Image.open(target) as image:
        return image.size


def pandoc_command(out_path):
    """The pandoc command that reads the prepared Markdown from stdin and writes ``out_path``."""
    return ["pandoc", "-f", PANDOC_FORMAT, "-t", "docx", "-o", out_path]


def svg_size(svg):
    """The ``width`` and ``height`` an SVG declares, in pixels."""
    width, height = re.search(r'<svg[^>]*\bwidth="([\d.]+)"[^>]*\bheight="([\d.]+)"', svg).groups()
    return float(width), float(height)


def figure_page(svg, scale):
    """A white page holding one SVG scaled by ``scale``, with the hooks ``chrome.Chrome`` calls."""
    return ("<!doctype html><html><head><meta charset='utf-8'><style>html,body{margin:0;background:#ffffff}"
            f"svg{{display:block;transform:scale({scale});transform-origin:0 0}}</style></head><body>{svg}"
            "<script>window.ready=document.fonts.ready;window.setTime=async t=>{"
            "for(const s of document.querySelectorAll('svg')){if(s.pauseAnimations){s.pauseAnimations();s.setCurrentTime(t)}}"
            "for(const a of document.getAnimations()){a.pause();a.currentTime=t*1000}"
            "await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return t}</script></body></html>")


def render_figures(text, out_dir):
    """
    Export every image of the paper into ``out_dir``.

    Parameters
    ----------
    text : str
        The paper's Markdown.
    out_dir : str

    Returns
    -------
    dict
        Exported file name to width in inches (``figure_width``).
    """
    import chrome  # needs websocket-client; imported here so the pure steps stay testable without it
    from PIL import Image

    os.makedirs(out_dir, exist_ok=True)
    widths = {}
    for source in images(text):
        path = os.path.normpath(os.path.join(PAPER_DIR, source))
        name = export_name(source)
        target = os.path.join(out_dir, name)
        if not source.lower().endswith(".svg"):
            with Image.open(path) as image:
                image.save(target)
        else:
            with open(path, encoding="utf-8") as file:
                svg = file.read()
            if source.endswith(".zh.svg"):
                svg = scenes.with_video_fonts(svg)
            width, height = svg_size(svg)
            animated = name.endswith(".gif")
            scale = GIF_SCALE if animated else STILL_SCALE
            size = (int(round(width * scale)), int(round(height * scale)))
            with tempfile.TemporaryDirectory(prefix="docx_figure_") as folder:
                page = os.path.join(folder, "page.html")
                with open(page, "w", encoding="utf-8") as file:
                    file.write(figure_page(svg, scale))
                with chrome.Chrome(*size, color_scheme="light") as browser:
                    browser.load(page)
                    if animated:
                        fps, seconds = gif_timing(source)
                        frames = [browser.capture(i / fps) for i in range(int(round(fps * seconds)))]
                    else:
                        frames = [browser.capture(0.0)]
            if animated:
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
                                "-filter_complex", "[0:v]split[a][b];[a]palettegen[p];[b][p]paletteuse",
                                "-loop", "0", target], input=b"".join(frames), check=True)
            else:
                with open(target, "wb") as file:
                    file.write(frames[0])
        widths[name] = figure_width(*figure_size(target, svg if source.lower().endswith(".svg") else None))
        print(f"{name}: {os.path.getsize(target) / 1e6:.2f} MB")
    return widths


def document_edits(lang):
    """
    The edits to ``word/document.xml`` after pandoc, for a language.

    Tables are laid out and sized to their content (for Chinese, a first-column
    bracketed part goes on its own line first), numbers in maths are set upright,
    figures are centred and kept with their captions, and the page gets its size
    and margins.

    Parameters
    ----------
    lang : str

    Returns
    -------
    callable
        Takes and returns the document XML.
    """
    def edit(xml):
        xml = format_tables(xml)
        if lang.startswith("zh"):
            xml = break_before_brackets(xml)
        xml = keep_figures_with_captions(set_table_widths(upright_numbers(xml), TEXT_WIDTH))
        return set_page(centre_figures(xml), MARGIN)

    return edit


def style_edits(lang):
    """
    The edits to ``word/styles.xml``: upright table captions (small capitals in
    English), and for Chinese the East Asian font and language.

    Parameters
    ----------
    lang : str

    Returns
    -------
    callable
        Takes and returns the styles XML.
    """
    east_asian = EAST_ASIAN.get(lang)

    def edit(xml):
        if east_asian:
            xml = set_east_asian_font(xml, *east_asian)
        return set_caption_style(xml, small_caps=not east_asian)

    return edit


def main(out_dir=OUT_DIR, lang="en"):
    """
    Export a language's paper and report what the Word file holds.

    Parameters
    ----------
    out_dir : str
    lang : str
        ``en`` or ``zh-CN`` (``docs/video/languages.py``).

    Returns
    -------
    str
        The Word file written, ``<paper>.docx``.

    Raises
    ------
    subprocess.CalledProcessError
        When pandoc or ffmpeg fails.
    """
    paper = languages.language(lang).paper
    with open(os.path.join(PAPER_DIR, paper), encoding="utf-8") as file:
        text = file.read()
    widths = render_figures(text, out_dir)
    out_path = os.path.join(out_dir, os.path.splitext(paper)[0] + ".docx")
    run = subprocess.run(pandoc_command(out_path), input=prepare_markdown(text, widths).encode("utf-8"),
                         cwd=out_dir, capture_output=True, check=True)
    warnings = [line for line in run.stderr.decode("utf-8", "replace").splitlines() if line.startswith("[WARNING]")]
    for line in warnings:
        print(line)
    finish(out_path, document_edits(lang), style_edits(lang))
    report = check_docx(out_path)
    print(", ".join(f"{key} {value!r}" for key, value in report.items()), f"; written to {os.path.relpath(out_path)}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=OUT_DIR, help="folder to write to (default: docs/paper/out)")
    parser.add_argument("--lang", default="en", choices=sorted(languages.LANGUAGES), help="the paper's language")
    options = parser.parse_args()
    main(options.out, options.lang)
