"""
When each narration segment plays and when each visual shows, from the
segments' durations.

Durations come from the audio files (``durations_from_audio``) or, before they
exist, from the word count (``estimated_durations``). ``build`` lays the
segments end to end with short pauses, opens a new visual span wherever a
segment switches the visual or a scene starts, and ends with the silent hold of
the references scene.
"""

import json
import os
import re
import subprocess

import languages
import script

LEAD_IN = 0.5
SEGMENT_PAUSE = 0.35
SCENE_PAUSE = 1.0
AUDIO_EXTENSIONS = (".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus")


class Cue:
    """
    One segment's narration on the timeline.

    Parameters
    ----------
    ident, scene : str
        Segment ID (``S04-03``) and scene ID (``S04``).
    text : str
    start, end : float
        Seconds from the start of the video.
    """

    def __init__(self, ident, scene, text, start, end):
        self.ident, self.scene, self.text, self.start, self.end = ident, scene, text, start, end


class Span:
    """
    A stretch of the video during which one visual shows.

    Parameters
    ----------
    scene : script.Scene
    visual : tuple of str
        ``(kind, name)``.
    start, end : float
        Seconds from the start of the video.
    """

    def __init__(self, scene, visual, start, end):
        self.scene, self.visual, self.start, self.end = scene, visual, start, end

    @property
    def duration(self):
        """Length in seconds."""
        return self.end - self.start


def estimated_durations(scenes, lang="en"):
    """
    Each segment's duration from its word count, at the language's speaking rate
    (``languages.Language.rate``).

    Parameters
    ----------
    scenes : list of script.Scene
    lang : str

    Returns
    -------
    dict
        Segment ID to seconds.
    """
    rate = languages.language(lang).rate
    return {s.ident: 60.0 * s.words() / rate for s in script.segments(scenes)}


def audio_files(folder):
    """
    The audio files in a folder, by segment ID (the file name without its extension).

    Parameters
    ----------
    folder : str

    Returns
    -------
    dict
        Segment ID to path; empty when the folder does not exist.
    """
    if not os.path.isdir(folder):
        return {}
    found = {}
    for name in sorted(os.listdir(folder)):
        stem, extension = os.path.splitext(name)
        if extension.lower() in AUDIO_EXTENSIONS:
            found[stem] = os.path.join(folder, name)
    return found


def probe_duration(path):
    """
    Length of a media file in seconds, read with ffprobe.

    Raises
    ------
    subprocess.CalledProcessError
        When ffprobe cannot read the file.
    """
    run = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
                         capture_output=True, text=True, check=True)
    return float(json.loads(run.stdout)["format"]["duration"])


# A pause in speech: at least this long, and this far below full scale
PAUSE_NOISE = "-35dB"
PAUSE_LENGTH = 0.2


def parse_silences(output):
    """
    The silences ffmpeg's ``silencedetect`` filter reports.

    Parameters
    ----------
    output : str
        ffmpeg's log, with its ``silence_start: <s>`` and ``silence_end: <s>`` lines.

    Returns
    -------
    list of tuple
        ``(start, end)`` in seconds, in order; a silence still open at the end
        of the file is left out.
    """
    starts = [float(s) for s in re.findall(r"silence_start: (-?[\d.]+)", output)]
    ends = [float(e) for e in re.findall(r"silence_end: (-?[\d.]+)", output)]
    return list(zip(starts, ends))


def speech_pauses(files):
    """
    The pauses in each segment's audio, read with ffmpeg's ``silencedetect``.

    Parameters
    ----------
    files : dict
        Segment ID to audio file.

    Returns
    -------
    dict
        Segment ID to its pauses, ``(start, end)`` in seconds from the file's start.

    Raises
    ------
    subprocess.CalledProcessError
        When ffmpeg cannot read a file.
    """
    pauses = {}
    for ident, path in files.items():
        run = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                              f"silencedetect=noise={PAUSE_NOISE}:d={PAUSE_LENGTH}", "-f", "null", "-"],
                             capture_output=True, text=True, check=True)
        pauses[ident] = parse_silences(run.stderr)
    return pauses


def durations_from_audio(scenes, folder):
    """
    Each segment's duration from its audio file, and the files that don't match.

    Parameters
    ----------
    scenes : list of script.Scene
    folder : str
        Holds one audio file per segment, named after it.

    Returns
    -------
    tuple
        ``(durations, files, missing, extra)``: segment ID to seconds and to
        path for the segments with a file, the segment IDs without a file, and
        the file names that match no segment.
    """
    files = audio_files(folder)
    idents = [s.ident for s in script.segments(scenes)]
    durations = {ident: probe_duration(files[ident]) for ident in idents if ident in files}
    missing = [ident for ident in idents if ident not in files]
    extra = sorted(set(files) - set(idents))
    return durations, {i: files[i] for i in durations}, missing, extra


def build(scenes, durations):
    """
    Lay out the video.

    Parameters
    ----------
    scenes : list of script.Scene
    durations : dict
        Segment ID to seconds, for every segment.

    Returns
    -------
    tuple
        ``(cues, spans, total)``: the segments in order, the visual spans in
        order (they join with no gap and start at 0), and the length of the
        video in seconds.
    """
    cues, spans = [], []
    t = LEAD_IN
    span_start = 0.0
    for scene in scenes:
        if scene.visual[0] in script.SILENT_KINDS:
            spans.append(Span(scene, scene.visual, span_start, t + script.REFERENCES_HOLD))
            t = span_start = spans[-1].end
            continue
        visual = scene.visual
        for segment in scene.segments:
            if segment.show and segment.show != visual:
                spans.append(Span(scene, visual, span_start, t))
                visual, span_start = segment.show, t
            end = t + durations[segment.ident]
            cues.append(Cue(segment.ident, scene.ident, segment.text, t, end))
            t = end + SEGMENT_PAUSE
        t += SCENE_PAUSE - SEGMENT_PAUSE
        spans.append(Span(scene, visual, span_start, t))
        span_start = t
    return cues, spans, t
