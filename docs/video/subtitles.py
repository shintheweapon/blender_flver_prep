"""
Subtitles for the video: each segment's narration broken into lines and timed
within the segment, written as SRT.

Lines are measured in display columns: a CJK character or full-width
punctuation mark takes two, anything else one. English breaks at spaces;
Chinese breaks between characters, preferably after its punctuation, and never
inside a run of Latin letters or digits such as ``FC_F_0000`` or ``1,437``.
"""

import re
import unicodedata

LINE_WIDTH = 42
MAX_LINES = 2
# How far back from the end of a full line a break after Chinese punctuation is preferred, in columns
PUNCTUATION_REACH = 6
WIDE = r"　-〿㐀-鿿豈-﫿＀-￯"
UNIT_RE = re.compile(rf"[{WIDE}]|[^\s{WIDE}]+|\s+")
BREAK_AFTER = set("，。；：、！？）")


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


def wrap(text, width=LINE_WIDTH):
    """
    Break text into lines of at most ``width`` columns.

    The units are single CJK characters and runs of other non-space
    characters (a word); spaces separate units and are not kept at a line's
    ends. A full line prefers to end after Chinese punctuation within
    ``PUNCTUATION_REACH`` columns of its end. A single unit wider than
    ``width`` gets a line of its own.

    Parameters
    ----------
    text : str
    width : int

    Returns
    -------
    list of str
    """
    lines, current = [], []

    def flush(units):
        line = "".join(units).strip()
        if line:
            lines.append(line)

    for unit in UNIT_RE.findall(text):
        if unit.isspace():
            if current:
                current.append(" ")
            continue
        if current and columns("".join(current) + unit) > width:
            if unit in BREAK_AFTER and len(current) > 1:
                # punctuation does not open a line: the unit before it moves down with it
                flush(current[:-1])
                current = [current[-1], unit]
                continue
            cut = None
            for index in range(len(current) - 1, -1, -1):
                if columns("".join(current[index + 1:])) > PUNCTUATION_REACH:
                    break
                if current[index] in BREAK_AFTER:
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


def entries(cues, width=LINE_WIDTH, max_lines=MAX_LINES):
    """
    Subtitle entries for the cues.

    Each cue's text is wrapped and cut into groups of ``max_lines`` lines; the
    cue's time is shared between the groups by their width in columns.

    Parameters
    ----------
    cues : list of timeline.Cue
    width, max_lines : int

    Returns
    -------
    list of tuple
        ``(start, end, lines)``, in time order.
    """
    result = []
    for cue in cues:
        lines = wrap(cue.text, width)
        groups = [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)]
        total = sum(columns(" ".join(group)) for group in groups)
        start = cue.start
        for group in groups:
            end = start + (cue.end - cue.start) * columns(" ".join(group)) / total
            result.append((start, end, group))
            start = end
    return result


def timestamp(seconds):
    """SRT time, ``HH:MM:SS,mmm``."""
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def srt(cues):
    """
    The cues as SRT text.

    Parameters
    ----------
    cues : list of timeline.Cue

    Returns
    -------
    str
    """
    blocks = []
    for number, (start, end, lines) in enumerate(entries(cues), 1):
        blocks.append(f"{number}\n{timestamp(start)} --> {timestamp(end)}\n" + "\n".join(lines) + "\n")
    return "\n".join(blocks)
