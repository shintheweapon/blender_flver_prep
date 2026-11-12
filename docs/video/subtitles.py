"""
Subtitles for the video: each segment's narration broken into lines and timed
within the segment, written as SRT.
"""

LINE_WIDTH = 42
MAX_LINES = 2


def wrap(text, width=LINE_WIDTH):
    """
    Break text into lines of at most ``width`` characters, at spaces.

    A single word longer than ``width`` gets a line of its own.

    Parameters
    ----------
    text : str
    width : int

    Returns
    -------
    list of str
    """
    lines, current = [], ""
    for word in text.split():
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines


def entries(cues, width=LINE_WIDTH, max_lines=MAX_LINES):
    """
    Subtitle entries for the cues.

    Each cue's text is wrapped and cut into groups of ``max_lines`` lines; the
    cue's time is shared between the groups by their number of characters.

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
        total = sum(len(" ".join(group)) for group in groups)
        start = cue.start
        for group in groups:
            end = start + (cue.end - cue.start) * len(" ".join(group)) / total
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
