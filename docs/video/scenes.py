"""
The page each visual of the video is captured from: an HTML document of
1920 by 1080 pixels, built from the paper and the figures in ``docs/figures/``.

Every page defines ``window.ready`` (a promise that settles once the page is
laid out) and ``window.setTime(t)`` (which moves its animations to ``t``
seconds and settles once that is painted), the two calls ``chrome.py`` makes.
"""

import html
import os
import re
import sys

import languages
import script

WIDTH, HEIGHT = 1920, 1080
STAGE_TOP = 100
STAGE_HEIGHT = 810
BACKGROUND = "#0d1117"
FONT = languages.language("en").page_font
KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/"

PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
{head}
<style>
:root {{ color-scheme: dark; }}
html, body {{ margin: 0; width: {width}px; height: {height}px; overflow: hidden; background: {background};
  font-family: {font}; color: #e6edf3; }}
.heading {{ position: absolute; left: 64px; top: 28px; font-size: 44px; color: #9198a1; }}
.stage {{ position: absolute; left: 0; top: {stage_top}px; width: {width}px; height: {stage}px; display: flex;
  align-items: center; justify-content: center; }}
.fit {{ transform-origin: center center; }}
.title {{ font-size: 84px; font-weight: 600; }}
.stack {{ display: flex; flex-direction: column; align-items: center; gap: 24px; }}
.stack svg {{ display: block; }}
.equation {{ font-size: 64px; display: flex; align-items: center; gap: 1.2em; }}
.equation .number {{ font-family: KaTeX_Main, serif; color: #9198a1; }}
.caption {{ text-align: center; font-size: 26px; letter-spacing: 0.04em; margin-bottom: 22px; }}
table {{ border-collapse: collapse; font-size: 26px; }}
th, td {{ border-bottom: 1px solid #30363d; padding: 10px 18px; text-align: left; }}
th {{ font-weight: 600; }}
img.shot {{ max-width: 1760px; max-height: {stage}px; }}
.references {{ width: 1760px; column-count: 2; column-gap: 72px; font-size: 22px; line-height: 1.4; }}
.references p {{ margin: 0 0 14px 0; break-inside: avoid; }}
.references h2 {{ column-span: all; font-size: 40px; font-weight: 600; margin: 0 0 24px 0; }}
code {{ font-family: Consolas, monospace; font-size: 0.92em; color: #e6edf3; }}
</style></head>
<body>{heading}<div class="stage"><div class="fit">{content}</div></div>
<script>
const MAX_UP = {max_up};
function fit() {{
  const box = document.querySelector('.fit'), r = box.getBoundingClientRect();
  const scale = Math.min(MAX_UP, 1760 / r.width, ({stage} - 40) / r.height);
  box.style.transform = 'scale(' + scale + ')';
}}
function painted() {{
  return new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)));
}}
async function prepare() {{
  {prepare}
  await document.fonts.ready;
  await Promise.all([...document.images].map(i => i.decode().catch(() => null)));
  fit();
  await painted();
}}
window.ready = prepare();
window.setTime = async function (t) {{
  for (const s of document.querySelectorAll('svg')) {{
    if (s.pauseAnimations) {{ s.pauseAnimations(); s.setCurrentTime(t); }}
  }}
  for (const a of document.getAnimations()) {{ a.pause(); a.currentTime = t * 1000; }}
  await painted();
  return t;
}};
</script></body></html>
"""

KATEX_HEAD = (f'<link rel="stylesheet" href="{KATEX}katex.min.css">\n'
              f'<script src="{KATEX}katex.min.js"></script>')
KATEX_RENDER = """for (const e of document.querySelectorAll('[data-tex]')) {
    katex.render(e.dataset.tex, e, {displayMode: e.dataset.display === '1', throwOnError: false});
  }"""


def figure_text(svg, lang="en"):
    """
    The figure's text in a language: unchanged for English.

    For Chinese, the figure's text is translated with the catalogue of
    ``docs/figures/zh_text.py`` (the same text as the committed ``.zh.svg``),
    and its font stack is led by the video's Chinese fonts, so figures and
    subtitles share one face.

    Parameters
    ----------
    svg : str
    lang : str

    Returns
    -------
    str
    """
    if not lang.startswith("zh"):
        return svg
    zh_text = _zh_text()
    video_stack = zh_text.FONT_STACK.replace("sans-serif", ",".join(languages.CJK_FONTS) + ",sans-serif")
    return zh_text.translate(svg).replace(zh_text.ZH_FONT_STACK, video_stack)


def _zh_text():
    """The figures' Chinese catalogue, ``docs/figures/zh_text.py``."""
    if script.FIGURES_DIR not in sys.path:
        sys.path.insert(0, script.FIGURES_DIR)
    import zh_text
    return zh_text


def paper_text(lang="en"):
    """
    The Markdown of the paper a language's video is built from.

    Parameters
    ----------
    lang : str

    Returns
    -------
    str
    """
    with open(script.paper_path(lang), encoding="utf-8") as file:
        return file.read()


def equation_tex(paper, number):
    """
    The TeX of a displayed equation of the paper, with its ``\\tag``.

    Raises
    ------
    KeyError
        When the paper has no equation with that number.
    """
    for block in re.findall(r"^\$\$\n(.*?)\n\$\$$", paper, flags=re.M | re.S):
        if f"\\tag{{{number}}}" in block:
            return block.strip()
    raise KeyError(f"no equation ({number})")


def inline(text):
    """
    Markdown inline marks as HTML: ``*italic*``, ```code``` and ``$maths$`` (left for KaTeX).

    Parameters
    ----------
    text : str

    Returns
    -------
    str
        HTML; maths becomes a span with a ``data-tex`` attribute.
    """
    parts = re.split(r"(\$[^$]+\$)", text)
    out = []
    for part in parts:
        if part.startswith("$") and part.endswith("$") and len(part) > 1:
            out.append(f'<span data-tex="{html.escape(part[1:-1], quote=True)}"></span>')
            continue
        escaped = html.escape(part, quote=False)
        escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
        escaped = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", escaped)
        out.append(escaped)
    return "".join(out)


def table(paper, numeral):
    """
    A table of the paper: its caption lines and its rows of cells.

    Returns
    -------
    tuple
        ``(caption, rows)``: the caption without the ``TABLE N`` line, and
        the rows as lists of Markdown cells, the header first.

    Raises
    ------
    KeyError
        When the paper has no table with that numeral.
    """
    labels = "|".join(script.TABLE_LABELS)
    match = re.search(rf'<p align="center">(?:{labels}) {numeral}<br>(.*?)</p>\n\n((?:\|.*\n)+)', paper)
    if not match:
        raise KeyError(f"no TABLE {numeral}")
    lines = [line for line in match.group(2).splitlines() if not re.match(r"^\|[-| ]+\|$", line)]
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    return match.group(1), rows


def references(paper):
    """
    The paper's reference list.

    Returns
    -------
    list of tuple
        ``(number, text)``, the text on one line, with its Markdown marks.
    """
    section = paper[paper.index(f"\n## {references_heading(paper)}\n"):]
    entries = re.findall(r"^\[(\d+)\] (.*?)(?=\n\n\[\d+\] |\n*\Z)", section, flags=re.M | re.S)
    return [(int(number), " ".join(text.split())) for number, text in entries]


def references_heading(paper):
    """
    The heading of the paper's reference list, as the paper writes it.

    Returns
    -------
    str
        ``References`` or ``参考文献``.

    Raises
    ------
    ValueError
        When the paper has neither heading.
    """
    for heading in script.REFERENCE_HEADINGS:
        if f"\n## {heading}\n" in paper:
            return heading
    raise ValueError("the paper has no reference list")


def table_label(paper):
    """
    The word the paper labels its tables with: ``TABLE`` or ``表``.

    Returns
    -------
    str
    """
    return next((label for label in script.TABLE_LABELS if f'<p align="center">{label} ' in paper),
                script.TABLE_LABELS[0])


def content(visual, paper, lang="en"):
    """
    The HTML inside the stage for a visual, and whether it needs KaTeX.

    Parameters
    ----------
    visual : tuple of str
        ``(kind, name)``, as in the script.
    paper : str
    lang : str

    Returns
    -------
    tuple
        ``(html, needs_katex, max_up)``: the content, whether KaTeX must load,
        and how far the content may be scaled up to fill the stage.

    Raises
    ------
    ValueError
        For an unknown kind.
    """
    kind, name = visual
    if kind == "title":
        return f'<div class="title">{html.escape(name)}</div>', False, 1.0
    if kind == "figure":
        parts = []
        for part in script.figure_files(name):
            with open(os.path.join(script.FIGURES_DIR, part), encoding="utf-8") as file:
                parts.append(figure_text(file.read(), lang))
        if len(parts) == 1:
            return parts[0], False, 2.4
        return '<div class="stack">' + "".join(f"<div>{p}</div>" for p in parts) + "</div>", False, 2.4
    if kind == "screenshot":
        uri = "file:///" + os.path.join(script.IMAGES_DIR, name).replace("\\", "/")
        return f'<img class="shot" src="{html.escape(uri, quote=True)}">', False, 2.0
    if kind == "equation":
        tex = re.sub(r"\\tag\{[^}]*\}", "", equation_tex(paper, name)).strip()
        return (f'<div class="equation"><span data-tex="{html.escape(tex, quote=True)}" data-display="1"></span>'
                f'<span class="number">({html.escape(name)})</span></div>'), True, 1.6
    if kind == "table":
        caption, rows = table(paper, name)
        head = "".join(f"<th>{inline(cell)}</th>" for cell in rows[0])
        body = "".join("<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>" for row in rows[1:])
        return (f'<div class="caption">{table_label(paper)} {html.escape(name)}<br>{html.escape(caption)}</div>'
                f"<table><tr>{head}</tr>{body}</table>"), True, 1.5
    if kind == "references":
        items = "".join(f"<p>[{number}] {inline(text)}</p>" for number, text in references(paper))
        return (f'<div class="references"><h2>{html.escape(references_heading(paper))}</h2>{items}</div>',
                False, 1.0)
    raise ValueError(f"unknown visual kind {kind}")


def page(scene, visual, paper, lang="en"):
    """
    The full page for one visual of a scene.

    Parameters
    ----------
    scene : script.Scene
    visual : tuple of str
    paper : str
    lang : str

    Returns
    -------
    str
        An HTML document of ``WIDTH`` by ``HEIGHT`` pixels.
    """
    body, needs_katex, max_up = content(visual, paper, lang)
    heading = "" if visual[0] in ("title", "references") else f'<div class="heading">{html.escape(scene.title)}</div>'
    return PAGE.format(head=KATEX_HEAD if needs_katex else "", width=WIDTH, height=HEIGHT,
                       font=languages.language(lang).page_font,
                       stage=STAGE_HEIGHT, stage_top=STAGE_TOP, background=BACKGROUND, heading=heading,
                       content=body, max_up=max_up, prepare=KATEX_RENDER if needs_katex else "")


def moves(visual):
    """
    Whether a visual changes over time (a figure animated with SMIL or CSS
    keyframes), so its span is captured frame by frame rather than once.
    """
    kind, name = visual
    if kind != "figure":
        return False
    for part in script.figure_files(name):
        with open(os.path.join(script.FIGURES_DIR, part), encoding="utf-8") as file:
            svg = file.read()
        if "<animate" in svg or "@keyframes" in svg:
            return True
    return False
