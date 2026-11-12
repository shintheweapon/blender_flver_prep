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
Chrome and the ``websocket-client`` package.
"""

import argparse
import io
import os
import re
import subprocess
import sys
import tempfile
import zipfile

PAPER_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.dirname(PAPER_DIR)
PAPER = os.path.join(PAPER_DIR, "ER_NORMAL_MAPS.md")
OUT_DIR = os.path.join(PAPER_DIR, "out")
VIDEO_DIR = os.path.join(DOCS_DIR, "video")
if VIDEO_DIR not in sys.path:
    sys.path.insert(0, VIDEO_DIR)

import scenes  # noqa: E402  (scenes.moves tells the animated figures apart; it imports no browser code)

STILL_SCALE = 2.0
GIF_SCALE = 1.5
GIF_TIMING = {"paper_axis_swap_animated.svg": (10, 30.0), "paper_dome_tilts.svg": (15, 5.0)}
MAX_WIDTH_INCHES = 6.5
PANDOC_FORMAT = "markdown-implicit_figures"
B = "\\"
TAG = re.compile(re.escape(B + "tag{") + r"([^}]*)\}")
TABLE_CAPTION = re.compile(r'<p align="center">TABLE ([IVXL]+)<br>(.*?)</p>')
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
      caption, ``Table: TABLE N. CAPTION``, which Word places above the table;
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
    text = TABLE_CAPTION.sub(lambda m: f"Table: TABLE {m.group(1)}. {m.group(2)}", text)

    def image(match):
        name = export_name(match.group(2))
        size = f"{{width={widths[name]:.2f}in}}" if name in widths else ""
        return f"![{match.group(1)}]({name}){size}"

    return IMAGE.sub(image, text)


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
        Exported file name to width in inches (capped at ``MAX_WIDTH_INCHES``).
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
                width_px = image.width
        else:
            with open(path, encoding="utf-8") as file:
                svg = file.read()
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
                        fps, seconds = GIF_TIMING[os.path.basename(source)]
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
            width_px = width
        widths[name] = min(width_px / 96.0, MAX_WIDTH_INCHES)
        print(f"{name}: {os.path.getsize(target) / 1e6:.2f} MB")
    return widths


BORDER_EDGES = ("top", "left", "bottom", "right", "insideH", "insideV")
TABLE_BORDERS = ("<w:tblBorders>" + "".join(f'<w:{edge} w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
                                            for edge in BORDER_EDGES) + "</w:tblBorders>")
TABLE_PROPERTIES = re.compile(r"<w:tblPr>(.*?)</w:tblPr>", re.S)


def add_table_borders(document_xml):
    """
    Give every table a grid: single 0.5 pt borders on all six edges, written into
    the table itself.

    pandoc's tables name a style it doesn't define, so they have no lines; a
    border set on the table carries over to Google Docs. A table that already
    has borders is left as it is.

    Parameters
    ----------
    document_xml : str
        ``word/document.xml``.

    Returns
    -------
    str
    """
    def bordered(match):
        properties = match.group(1)
        if "<w:tblBorders" in properties:
            return match.group(0)
        style = re.match(r"\s*<w:tblStyle[^>]*/>", properties)
        cut = style.end() if style else 0
        return f"<w:tblPr>{properties[:cut]}{TABLE_BORDERS}{properties[cut:]}</w:tblPr>"

    return TABLE_PROPERTIES.sub(bordered, document_xml)


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
        ``equations``, ``tables``, ``bordered_tables``, ``images``, ``gifs``,
        ``tex_left`` (TeX commands left in the text), ``author`` (the file's
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
        "images": len(media),
        "gifs": sum(n.lower().endswith(".gif") for n in media),
        "tex_left": len(re.findall(re.escape(B) + r"(?:vec|frac|partial|times|hat)\b", text_only)),
        "author": author.group(1) if author else "",
    }


def main(out_dir=OUT_DIR):
    """
    Export the paper and report what the Word file holds.

    Returns
    -------
    str
        The Word file written.

    Raises
    ------
    subprocess.CalledProcessError
        When pandoc or ffmpeg fails.
    """
    with open(PAPER, encoding="utf-8") as file:
        text = file.read()
    widths = render_figures(text, out_dir)
    out_path = os.path.join(out_dir, "ER_NORMAL_MAPS.docx")
    run = subprocess.run(pandoc_command(out_path), input=prepare_markdown(text, widths).encode("utf-8"),
                         cwd=out_dir, capture_output=True, check=True)
    warnings = [line for line in run.stderr.decode("utf-8", "replace").splitlines() if line.startswith("[WARNING]")]
    for line in warnings:
        print(line)
    rewrite_document(out_path, add_table_borders)
    report = check_docx(out_path)
    print(", ".join(f"{key} {value!r}" for key, value in report.items()), f"; written to {os.path.relpath(out_path)}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=OUT_DIR, help="folder to write to (default: docs/paper/out)")
    main(parser.parse_args().out)
