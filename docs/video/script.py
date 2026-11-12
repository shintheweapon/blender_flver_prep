"""
The narration of the paper's video: read from ``script.<lang>.md`` and
exported for a speech tool, one text file per segment.

The script's format is described at the top of ``script.en.md``. Run
``python docs/video/script.py [lang]`` to write the export to
``docs/video/out/tts/<lang>/`` (git-ignored).
"""

import os
import re
import sys

VIDEO_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.dirname(VIDEO_DIR)
FIGURES_DIR = os.path.join(DOCS_DIR, "figures")
IMAGES_DIR = os.path.join(DOCS_DIR, "paper", "images")
PAPER = os.path.join(DOCS_DIR, "paper", "ER_NORMAL_MAPS.md")
OUT_DIR = os.path.join(VIDEO_DIR, "out")

KINDS = ("title", "figure", "equation", "table", "screenshot", "references")
SILENT_KINDS = ("references",)
REFERENCES_HOLD = 10.0
WORDS_PER_MINUTE = 145
SCENE_RE = re.compile(r"^## (S\d\d) (.+)$")
VISUAL_RE = re.compile(r"^Visual: (\w+)(?: (.+))?$")
SEGMENT_RE = re.compile(r"^\*\*(S\d\d-\d\d)\*\*$")
SHOW_RE = re.compile(r"^\{show: (\w+) ([^}]+)\}\s*")


class Segment:
    """
    One narration file: its ID, its spoken text, and the visual it switches to.

    Parameters
    ----------
    ident : str
        ``S04-03``: scene 4, segment 3.
    text : str
        The narration, on one line.
    show : tuple of str or None
        ``(kind, name)`` of the visual shown from this segment on, or None to
        keep the current one.
    """

    def __init__(self, ident, text, show=None):
        self.ident, self.text, self.show = ident, text, show

    def words(self):
        """Number of words in the narration."""
        return len(self.text.split())


class Scene:
    """
    A section of the video: its ID, title, first visual and segments.

    Parameters
    ----------
    ident : str
        ``S04``.
    title : str
    visual : tuple of str
        ``(kind, name)`` of the first visual.
    segments : list of Segment
    """

    def __init__(self, ident, title, visual, segments):
        self.ident, self.title, self.visual, self.segments = ident, title, visual, segments


def script_path(lang="en"):
    """Path of the script for a language code."""
    return os.path.join(VIDEO_DIR, f"script.{lang}.md")


def parse(text):
    """
    Read a script.

    Parameters
    ----------
    text : str
        The contents of a ``script.<lang>.md`` file.

    Returns
    -------
    list of Scene

    Raises
    ------
    ValueError
        When a segment or a visual line comes before any scene, a scene has no
        visual, or a scene without segments has a visual other than a silent
        one (``SILENT_KINDS``), or a silent scene has segments.
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    scenes, lines = [], []
    scene = segment = None

    def close_segment():
        nonlocal segment, lines
        if segment is None:
            return
        body = " ".join(line.strip() for line in lines if line.strip())
        show = None
        match = SHOW_RE.match(body)
        if match:
            show, body = (match.group(1), match.group(2).strip()), body[match.end():]
        scene.segments.append(Segment(segment, body.strip(), show))
        segment, lines = None, []

    for line in text.splitlines():
        if SCENE_RE.match(line):
            close_segment()
            ident, title = SCENE_RE.match(line).groups()
            scene = Scene(ident, title.strip(), None, [])
            scenes.append(scene)
        elif VISUAL_RE.match(line):
            if scene is None:
                raise ValueError(f"visual before any scene: {line}")
            kind, name = VISUAL_RE.match(line).groups()
            scene.visual = (kind, (name or "").strip())
        elif SEGMENT_RE.match(line):
            if scene is None:
                raise ValueError(f"segment before any scene: {line}")
            close_segment()
            segment = SEGMENT_RE.match(line).group(1)
        elif segment is not None:
            lines.append(line)
    close_segment()
    for scene in scenes:
        if scene.visual is None:
            raise ValueError(f"scene {scene.ident} has no visual")
        silent = scene.visual[0] in SILENT_KINDS
        if silent == bool(scene.segments):
            raise ValueError(f"scene {scene.ident}: only a {', '.join(SILENT_KINDS)} scene has no segments")
    return scenes


def load(lang="en"):
    """
    Read the script of a language.

    Parameters
    ----------
    lang : str
        Language code, as in ``script.en.md``.

    Returns
    -------
    list of Scene
    """
    with open(script_path(lang), encoding="utf-8") as file:
        return parse(file.read())


def segments(scenes):
    """Every segment of the script, in order."""
    return [segment for scene in scenes for segment in scene.segments]


def figure_files(name):
    """
    The SVG files of a figure visual: one, or several joined by `` + `` to be stacked
    top to bottom in one frame.

    Parameters
    ----------
    name : str

    Returns
    -------
    list of str
    """
    return [part.strip() for part in name.split(" + ")]


def visual_exists(kind, name, paper_text):
    """
    Whether a visual named in the script can be found.

    Parameters
    ----------
    kind : str
        One of ``KINDS``.
    name : str
        A file name for figures and screenshots (figures joined by `` + `` are
        stacked in one frame), an equation number, a table numeral, or the text
        of a title card.
    paper_text : str
        The paper, to look up equations and tables.

    Returns
    -------
    bool
    """
    if kind == "title":
        return bool(name.strip())
    if kind == "figure":
        return all(os.path.isfile(os.path.join(FIGURES_DIR, part)) for part in figure_files(name))
    if kind == "screenshot":
        return os.path.isfile(os.path.join(IMAGES_DIR, name))
    if kind == "equation":
        return f"\\tag{{{name}}}" in paper_text
    if kind == "table":
        return f"TABLE {name}<br>" in paper_text
    if kind == "references":
        return "\n## References\n" in paper_text
    return False


def export(scenes, lang="en", out_dir=None):
    """
    Write the narration for a speech tool.

    Writes one ``<ID>.txt`` per segment and ``all.txt``, which holds every
    segment as ``<ID><tab><text>`` on its own line.

    Parameters
    ----------
    scenes : list of Scene
    lang : str
    out_dir : str or None
        The folder to write to; ``docs/video/out/tts/<lang>/`` when None.

    Returns
    -------
    str
        The folder written to.
    """
    folder = out_dir or os.path.join(OUT_DIR, "tts", lang)
    os.makedirs(folder, exist_ok=True)
    rows = []
    for segment in segments(scenes):
        with open(os.path.join(folder, f"{segment.ident}.txt"), "w", encoding="utf-8", newline="\n") as file:
            file.write(segment.text + "\n")
        rows.append(f"{segment.ident}\t{segment.text}")
    with open(os.path.join(folder, "all.txt"), "w", encoding="utf-8", newline="\n") as file:
        file.write("\n".join(rows) + "\n")
    return folder


def main(lang="en"):
    """Export the script of a language and print a summary."""
    scenes = load(lang)
    folder = export(scenes, lang)
    words = sum(segment.words() for segment in segments(scenes))
    print(f"{len(segments(scenes))} segments, {words} words, about {words / WORDS_PER_MINUTE:.1f} minutes; "
          f"written to {os.path.relpath(folder, DOCS_DIR)}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
