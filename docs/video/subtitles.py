"""
Subtitles for the video: each segment's narration broken into lines and timed
within the segment, written as SRT.

Lines are measured in display columns: a CJK character or full-width
punctuation mark takes two, anything else one. English breaks at spaces.
Chinese breaks between words when a word splitter is given (``jieba_words``),
otherwise between characters; in both cases preferably after its punctuation,
never before it, and never inside a run of Latin letters or digits such as
``FC_F_0000`` or ``1,437``.

A segment's lines are shown in groups of up to two. English groups follow its
sentences (``sentence_groups``), as the narration pauses at their ends; other
languages fill each group in turn.

Each segment's time is shared between its groups of lines by their width; where
the segment's audio has a pause near a boundary between two groups, the
boundary moves to that pause.
"""

import functools
import math
import os
import re
import unicodedata
from collections import namedtuple

LINE_WIDTH = 42
MAX_LINES = 2
# How far back from the end of a full line a break after Chinese punctuation is preferred, in columns
PUNCTUATION_REACH = 6
# How far a boundary between two groups may move to reach a pause, and the ends of a segment ignored, in seconds
SNAP_REACH = 1.5
SNAP_MARGIN = 0.3
WIDE = r"　-〿㐀-鿿豈-﫿＀-￯"
RUN_RE = re.compile(rf"[{WIDE}]+|[^\s{WIDE}]+|\s+")
WIDE_RE = re.compile(rf"[{WIDE}]")
BREAK_AFTER = set("，。；：、！？）")
# Where an English sentence (or clause the narration pauses after) ends, and the window around an even cut of a
# long sentence, in columns before and after it, in which a comma is taken instead
SENTENCE_END = re.compile(r"(?<=[.?!;:])\s+")
COMMA_BEFORE = 12
COMMA_AFTER = 4
GLOSSARY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "paper", "glossary.zh-CN.md")

Layout = namedtuple("Layout", "width max_lines split sentences", defaults=(LINE_WIDTH, MAX_LINES, None, False))
Layout.__doc__ = """
How subtitle lines are made.

Parameters
----------
width : int
    Columns a line may take.
max_lines : int
    Lines shown at once.
split : callable or None
    Turns a run of CJK text into words (``jieba_words``); None breaks it into
    single characters.
sentences : bool
    Groups of lines follow the sentences (``sentence_groups``); False fills
    each group in turn.
"""


def columns(text):
    """
    Display width of text: two columns for each wide (CJK) character, one otherwise.

    Parameters
    ----------
    text : str

    Returns
    -------
    int
    """
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def units(text, width=LINE_WIDTH, split=None):
    """
    The units a line is built from: words of CJK text, runs of other
    non-space characters, and single spaces.

    Parameters
    ----------
    text : str
    width : int
        A CJK word wider than this is broken into characters.
    split : callable or None
        Turns a CJK run into words; None gives single characters.

    Returns
    -------
    list of str
    """
    found = []
    for run in RUN_RE.findall(text):
        if run.isspace():
            found.append(" ")
        elif WIDE_RE.match(run):
            for word in (split(run) if split else run):
                found.extend(word if columns(word) > width else [word])
        else:
            found.append(run)
    return found


def wrap(text, width=LINE_WIDTH, split=None):
    """
    Break text into lines of at most ``width`` columns.

    Spaces separate units and are not kept at a line's ends. A full line
    prefers to end after Chinese punctuation within ``PUNCTUATION_REACH``
    columns of its end, and punctuation never opens a line. A single unit wider
    than ``width`` gets a line of its own.

    Parameters
    ----------
    text : str
    width : int
    split : callable or None
        The word splitter for CJK text (see ``units``).

    Returns
    -------
    list of str
    """
    lines, current = [], []

    def flush(parts):
        line = "".join(parts).strip()
        if line:
            lines.append(line)

    for unit in units(text, width, split):
        if unit == " ":
            if current:
                current.append(" ")
            continue
        if current and columns("".join(current) + unit) > width:
            if unit[0] in BREAK_AFTER and len(current) > 1:
                # punctuation does not open a line: the unit before it moves down with it
                flush(current[:-1])
                current = [current[-1], unit]
                continue
            cut = None
            for index in range(len(current) - 1, -1, -1):
                if columns("".join(current[index + 1:])) > PUNCTUATION_REACH:
                    break
                if current[index][-1:] in BREAK_AFTER:
                    cut = index
                    break
            if cut is not None and cut < len(current) - 1:
                flush(current[:cut + 1])
                current = current[cut + 1:]
                while current and current[0] == " ":
                    current.pop(0)
                if current and columns("".join(current) + unit) > width:
                    flush(current)
                    current = []
            else:
                flush(current)
                current = []
        current.append(unit)
    flush(current)
    return lines


def even_parts(sentence, layout=Layout()):
    """
    A sentence too long for one group, cut into the fewest groups of even width.

    The sentence needs ``ceil(lines / layout.max_lines)`` groups. Each cut falls
    at the first comma from ``COMMA_BEFORE`` columns before to ``COMMA_AFTER``
    columns after its even point, when the rest still fits in the groups left;
    otherwise after the word that reaches the point. A sentence that fits in
    one group is that group.

    Parameters
    ----------
    sentence : str
    layout : Layout

    Returns
    -------
    list of list of str
        The groups' lines.
    """
    lines = wrap(sentence, layout.width, layout.split)
    if len(lines) <= layout.max_lines:
        return [lines]
    count = math.ceil(len(lines) / layout.max_lines)
    words = sentence.split()
    total = columns(" ".join(words))
    def rest_fits(index):
        rest = " ".join(words[index + 1:])
        return len(wrap(rest, layout.width, layout.split)) <= (count - len(parts) - 1) * layout.max_lines

    parts, current, taken = [], [], []
    for index, word in enumerate(words):
        current.append(word)
        taken.append(word)
        done = columns(" ".join(taken))
        target = total * (len(parts) + 1) / count
        at_comma = (word.endswith(",") and target - COMMA_BEFORE <= done <= target + COMMA_AFTER
                    and rest_fits(index))
        if len(parts) < count - 1 and (at_comma or done >= target):
            parts.append(current)
            current = []
    if current:
        parts.append(current)
    found = []
    for part in parts:
        part_lines = wrap(" ".join(part), layout.width, layout.split)
        found += [part_lines[i:i + layout.max_lines] for i in range(0, len(part_lines), layout.max_lines)]
    return found


def sentence_groups(text, layout=Layout()):
    """
    Groups of lines that follow the sentences.

    Sentences end at ``SENTENCE_END``. Whole sentences are packed into a group
    while its lines fit in ``layout.max_lines``; a sentence too long for one
    group closes the group before it and is cut by ``even_parts``.

    Parameters
    ----------
    text : str
    layout : Layout

    Returns
    -------
    list of list of str
        The groups' lines, in order.
    """
    found, current = [], []

    def close():
        if current:
            found.append(wrap(" ".join(current), layout.width, layout.split))
            current.clear()

    for sentence in SENTENCE_END.split(text.strip()):
        if not sentence:
            continue
        if len(wrap(sentence, layout.width, layout.split)) > layout.max_lines:
            close()
            found.extend(even_parts(sentence, layout))
            continue
        if current and len(wrap(" ".join(current + [sentence]), layout.width, layout.split)) > layout.max_lines:
            close()
        current.append(sentence)
    close()
    return found


def groups(text, layout=Layout()):
    """
    A segment's lines in the groups shown at once.

    Parameters
    ----------
    text : str
    layout : Layout
        With ``sentences``, groups follow the sentences (``sentence_groups``);
        otherwise the lines are cut into groups of ``max_lines`` in turn.

    Returns
    -------
    list of list of str
    """
    if layout.sentences:
        return sentence_groups(text, layout)
    lines = wrap(text, layout.width, layout.split)
    return [lines[i:i + layout.max_lines] for i in range(0, len(lines), layout.max_lines)]


def snap(boundaries, pauses, start, end):
    """
    Move each boundary between two groups to the middle of the nearest pause.

    A pause counts when it lies within the segment, at least ``SNAP_MARGIN``
    seconds from either end, after the previous boundary, and with its middle
    within ``SNAP_REACH`` of the boundary; a boundary with no such pause keeps
    its time.

    Parameters
    ----------
    boundaries : list of float
        Times between groups, in order.
    pauses : list of tuple
        ``(start, end)`` pauses, in the same time as the boundaries.
    start, end : float
        The segment's start and end.

    Returns
    -------
    list of float
        The boundaries, in order.
    """
    result, previous = [], start
    middles = [(a + b) / 2 for a, b in pauses if a >= start + SNAP_MARGIN and b <= end - SNAP_MARGIN]
    for boundary in boundaries:
        near = [m for m in middles if m > previous and abs(m - boundary) <= SNAP_REACH]
        moved = min(near, key=lambda m: abs(m - boundary)) if near else max(boundary, previous)
        result.append(moved)
        previous = moved
    return result


def entries(cues, layout=Layout(), pauses=None):
    """
    Subtitle entries for the cues.

    Each cue's text is wrapped and cut into groups of up to
    ``layout.max_lines`` lines (``groups``); the cue's time is shared between the groups by their width in
    columns, and each boundary between groups then moves to a nearby pause in
    the cue's audio (``snap``).

    Parameters
    ----------
    cues : list of timeline.Cue
    layout : Layout
    pauses : dict or None
        Segment ID to its pauses, ``(start, end)`` in seconds from the start
        of its audio; None, or a missing ID, keeps the width-based times.

    Returns
    -------
    list of tuple
        ``(start, end, lines)``, in time order.
    """
    result = []
    for cue in cues:
        shown = groups(cue.text, layout)
        widths = [columns(" ".join(group)) for group in shown]
        times, elapsed = [], 0
        for width in widths[:-1]:
            elapsed += width
            times.append(cue.start + (cue.end - cue.start) * elapsed / sum(widths))
        found = [(cue.start + a, cue.start + b) for a, b in (pauses or {}).get(cue.ident, [])]
        times = snap(times, found, cue.start, cue.end)
        for group, start, end in zip(shown, [cue.start] + times, times + [cue.end]):
            result.append((start, end, group))
    return result


def clip(found, until):
    """
    The entries shown before ``until`` seconds: later ones are dropped and the
    last one kept ends at ``until``. Each entry keeps its own timing.

    Parameters
    ----------
    found : list of tuple
        ``(start, end, lines)``, as from ``entries``.
    until : float or None
        None keeps every entry.

    Returns
    -------
    list of tuple
    """
    if until is None:
        return list(found)
    return [(start, min(end, until), lines) for start, end, lines in found if start < until]


def timestamp(seconds):
    """SRT time, ``HH:MM:SS,mmm``."""
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def srt(found):
    """
    Entries as SRT text.

    Parameters
    ----------
    found : list of tuple
        ``(start, end, lines)``, as from ``entries`` or ``clip``.

    Returns
    -------
    str
    """
    blocks = []
    for number, (start, end, lines) in enumerate(found, 1):
        blocks.append(f"{number}\n{timestamp(start)} --> {timestamp(end)}\n" + "\n".join(lines) + "\n")
    return "\n".join(blocks)


def glossary_terms(path=GLOSSARY):
    """
    The Chinese terms of the glossary's table, so a word splitter keeps them whole.

    Parameters
    ----------
    path : str
        ``docs/paper/glossary.zh-CN.md``.

    Returns
    -------
    list of str
        The 中文 column's entries, split at commas, in table order.
    """
    terms = []
    with open(path, encoding="utf-8") as file:
        for line in file:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and line.startswith("|") and WIDE_RE.search(cells[1]) and cells[1] != "中文":
                terms += [term.strip() for term in re.split(r"[,，]", cells[1]) if WIDE_RE.search(term)]
    return terms


@functools.lru_cache(maxsize=None)
def _jieba():
    """jieba, with the glossary's terms added as words (imported only to render Chinese subtitles)."""
    import logging

    import jieba
    jieba.setLogLevel(logging.WARNING)
    for term in glossary_terms():
        jieba.add_word(term)
    return jieba


def jieba_words(text):
    """
    Chinese text cut into words by jieba, keeping the glossary's terms whole.

    Parameters
    ----------
    text : str

    Returns
    -------
    list of str

    Raises
    ------
    ImportError
        When the ``jieba`` package is not installed.
    """
    return _jieba().lcut(text)
