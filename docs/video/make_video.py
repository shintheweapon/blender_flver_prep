"""
Render the paper's video: capture each visual span from its page, join the
clips, lay the narration on its timeline and burn in the subtitles.

Run ``python docs/video/make_video.py`` for the full video (1920 by 1080, 30
frames a second) or ``python docs/video/make_video.py --draft`` for a quick one
(960 by 540, 15 frames a second). With audio files in
``docs/video/audio/<lang>/`` their lengths set the timing and the video has
sound; without them, durations are estimated from the word count and the video
is silent. Everything is written under ``docs/video/out/`` (git-ignored);
clips are cached there, so a second run renders only what changed.
"""

import argparse
import hashlib
import os
import subprocess
import tempfile

import languages
import scenes
import script
import subtitles
import timeline

FULL = (1920, 1080, 30)
DRAFT = (960, 540, 15)
SUBTITLE_TOP = 924
# The word splitters a language may name (``languages.Language.words``)
WORD_SPLITTERS = {None: None, "jieba": subtitles.jieba_words}


def subtitle_style(font):
    """
    The libass style of the burned-in subtitles, in a font family.

    An opaque box per line (BorderStyle 3, alpha 00): where a subtitle's line
    boxes overlap, an opaque box keeps one shade, while a see-through one
    doubles its shade there.

    Parameters
    ----------
    font : str
        A font family name.

    Returns
    -------
    str
    """
    return (f"FontName={font},FontSize=13.2,PrimaryColour=&H00FFFFFF,BorderStyle=3,Outline=1,"
            "OutlineColour=&H00221B16,Shadow=0,MarginV=14")


SUBTITLE_STYLE = subtitle_style("Segoe UI")


def pick_font(fonts, available):
    """
    The first font family that is installed.

    Parameters
    ----------
    fonts : sequence of str
        The families in order of preference.
    available : callable
        Takes a family name, returns whether it is installed.

    Returns
    -------
    str

    Raises
    ------
    LookupError
        When none of them is installed.
    """
    for font in fonts:
        if available(font):
            return font
    raise LookupError(f"none of these fonts is installed: {', '.join(fonts)}")


# Whether a family is installed: text drawn in it, with a generic fallback, measures differently from the fallback
# alone (``document.fonts.check`` answers true for any family that needs no download, installed or not)
FONT_PROBE = """(() => {{
  const c = document.createElement('canvas').getContext('2d'), s = '汉字测试 Abg 0123';
  const w = f => {{ c.font = f; return c.measureText(s).width; }};
  return ['monospace', 'serif', 'sans-serif'].some(b => w('32px "{font}", ' + b) !== w('32px ' + b));
}})()"""


def subtitle_font(lang):
    """
    The subtitle family for a language: its only one, or the first of its list
    that Chrome finds installed (``FONT_PROBE``).

    Raises
    ------
    LookupError
        When none of the language's families is installed.
    """
    fonts = languages.language(lang).subtitle_fonts
    if len(fonts) == 1:
        return fonts[0]
    import chrome
    with chrome.Chrome(64, 64) as browser:
        return pick_font(fonts, lambda font: bool(browser.evaluate(FONT_PROBE.format(font=font))))


def ffmpeg(*args, cwd=None):
    """
    Run ffmpeg quietly.

    Raises
    ------
    subprocess.CalledProcessError
        When ffmpeg fails; its error output is in the exception.
    """
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], check=True, cwd=cwd,
                   capture_output=True, text=True)


def frame_counts(spans, fps):
    """
    Frames per span, from rounded start and end frames so the clips add up to the
    whole video without drift.

    Parameters
    ----------
    spans : list of timeline.Span
    fps : int

    Returns
    -------
    list of int
    """
    return [round(span.end * fps) - round(span.start * fps) for span in spans]


def until_spans(spans, cues, until):
    """
    The spans and cues of the video's first ``until`` seconds, for a cheap partial render.

    Spans that start at or after ``until`` are dropped and the last one kept is cut
    to end at ``until``; cues are kept when they start before ``until``, cut likewise.

    Parameters
    ----------
    spans : list of timeline.Span
    cues : list of timeline.Cue
    until : float or None
        Seconds; None keeps everything.

    Returns
    -------
    tuple
        ``(spans, cues, total)``.
    """
    if until is None:
        return spans, cues, spans[-1].end
    kept = [timeline.Span(s.scene, s.visual, s.start, min(s.end, until)) for s in spans if s.start < until]
    shown = [timeline.Cue(c.ident, c.scene, c.text, c.start, min(c.end, until)) for c in cues if c.start < until]
    return kept, shown, kept[-1].end


def encode(source_args, frames, size, fps, path):
    """Encode frames into an H.264 clip of exactly ``frames`` frames."""
    width, height = size
    ffmpeg(*source_args, "-frames:v", str(frames), "-vf", f"scale={width}:{height}:flags=lanczos,format=yuv420p",
           "-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "18", path)


def render_span(browser, page_path, span, frames, size, fps, path):
    """
    Capture one span and encode it as a clip.

    A still visual is captured once and repeated; a moving one is captured
    frame by frame, with the animation's time counted from the span's start.
    """
    with tempfile.TemporaryDirectory(prefix="video_frames_") as folder:
        browser.load(page_path)
        if scenes.moves(span.visual):
            for index in range(frames):
                with open(os.path.join(folder, f"{index:05d}.png"), "wb") as file:
                    file.write(browser.capture(index / fps))
            encode(["-framerate", str(fps), "-i", os.path.join(folder, "%05d.png")], frames, size, fps, path)
        else:
            still = os.path.join(folder, "still.png")
            with open(still, "wb") as file:
                file.write(browser.capture(0.0))
            encode(["-loop", "1", "-framerate", str(fps), "-i", still], frames, size, fps, path)


def narration_track(cues, files, total, path):
    """
    Lay each segment's audio at its cue's start, in one track of ``total`` seconds.

    Parameters
    ----------
    cues : list of timeline.Cue
    files : dict
        Segment ID to audio file.
    total : float
    path : str
        The WAV file to write.
    """
    inputs, chains, labels = [], [], []
    for index, cue in enumerate(cue for cue in cues if cue.ident in files):
        inputs += ["-i", files[cue.ident]]
        delay = int(round(cue.start * 1000))
        chains.append(f"[{index}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={delay}|{delay}[a{index}]")
        labels.append(f"[a{index}]")
    graph = ";".join(chains) + ";" + "".join(labels) + \
        f"amix=inputs={len(labels)}:normalize=0,apad,atrim=0:{total:.3f}[out]"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as file:
        file.write(graph)
    try:
        ffmpeg(*inputs, "-/filter_complex", file.name, "-map", "[out]", "-c:a", "pcm_s16le", path)
    finally:
        os.remove(file.name)


def main(lang="en", draft=False, until=None):
    """
    Render the video of a language.

    Parameters
    ----------
    lang : str
    draft : bool
        A quick, smaller render.
    until : float or None
        Render only the first ``until`` seconds.

    Returns
    -------
    str
        The video written.
    """
    width, height, fps = DRAFT if draft else FULL
    all_scenes = script.load(lang)
    audio_dir = os.path.join(script.VIDEO_DIR, "audio", lang)
    durations, files, missing, extra = timeline.durations_from_audio(all_scenes, audio_dir)
    if extra:
        print("audio files that match no segment:", ", ".join(extra))
    if missing:
        estimated = timeline.estimated_durations(all_scenes, lang)
        print(f"{len(missing)} of {len(estimated)} segments have no audio; their length is estimated"
              + (f" ({', '.join(missing[:5])}{', ...' if len(missing) > 5 else ''})" if files else ""))
        durations = {ident: durations.get(ident, estimated[ident]) for ident in estimated}
    full_cues, spans, total = timeline.build(all_scenes, durations)
    spans, cues, total = until_spans(spans, full_cues, until)

    out = os.path.join(script.OUT_DIR)
    cache, pages = os.path.join(out, "cache"), os.path.join(out, "pages")
    os.makedirs(cache, exist_ok=True)
    os.makedirs(pages, exist_ok=True)
    name = f"normal_maps.{lang}{'.draft' if draft else ''}{f'.until{until:g}' if until else ''}"
    # subtitles are timed on the whole cues and only then cut, so a cut segment keeps its own timing
    language = languages.language(lang)
    layout = subtitles.Layout(split=WORD_SPLITTERS[language.words], sentences=language.subtitle_sentences)
    shown = subtitles.clip(subtitles.entries(full_cues, layout, timeline.speech_pauses(files)), until)
    with open(os.path.join(out, f"{name}.srt"), "w", encoding="utf-8", newline="\n") as file:
        file.write(subtitles.srt(shown))

    paper = scenes.paper_text(lang)
    font = subtitle_font(lang)
    print(f"subtitles in {font}")
    clips, browser = [], None
    try:
        for index, (span, frames) in enumerate(zip(spans, frame_counts(spans, fps))):
            html = scenes.page(span.scene, span.visual, paper, lang)
            key = hashlib.sha1(f"{html}|{frames}|{width}x{height}@{fps}|{scenes.moves(span.visual)}".encode()) \
                .hexdigest()[:16]
            clip = os.path.join(cache, f"{key}.mp4")
            if not os.path.exists(clip):
                page_path = os.path.join(pages, f"{index:03d}_{span.scene.ident}.html")
                with open(page_path, "w", encoding="utf-8") as file:
                    file.write(html)
                if browser is None:
                    import chrome
                    browser = chrome.Chrome(scenes.WIDTH, scenes.HEIGHT)
                print(f"rendering {span.scene.ident} {span.visual[0]} {span.visual[1]} ({frames} frames)", flush=True)
                render_span(browser, page_path, span, frames, (width, height), fps, clip + ".part.mp4")
                os.replace(clip + ".part.mp4", clip)
            clips.append(clip)
    finally:
        if browser is not None:
            browser.close()

    joined = os.path.join(out, f"{name}.video.mp4")
    with open(os.path.join(out, "clips.txt"), "w", encoding="utf-8", newline="\n") as file:
        file.write("".join(f"file '{clip.replace(os.sep, '/')}'\n" for clip in clips))
    ffmpeg("-f", "concat", "-safe", "0", "-i", os.path.join(out, "clips.txt"), "-c", "copy", joined)

    args = ["-i", f"{name}.video.mp4"]
    if files:
        narration_track(cues, files, total, os.path.join(out, f"{name}.wav"))
        args += ["-i", f"{name}.wav", "-c:a", "aac", "-b:a", "192k"]
    ffmpeg(*args, "-vf", f"subtitles={name}.srt:force_style='{subtitle_style(font)}'", "-c:v", "libx264",
           "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", f"{name}.mp4", cwd=out)
    os.remove(joined)
    result = os.path.join(out, f"{name}.mp4")
    print(f"{len(cues)} segments, {len(spans)} visual spans, {total / 60:.1f} minutes: {os.path.relpath(result)}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("lang", nargs="?", default="en")
    parser.add_argument("--draft", action="store_true", help="960 by 540 at 15 frames a second")
    parser.add_argument("--until", type=float, help="render only the first SECONDS", metavar="SECONDS")
    options = parser.parse_args()
    main(options.lang, options.draft, options.until)
