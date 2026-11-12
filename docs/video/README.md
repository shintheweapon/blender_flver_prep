# The paper's video

A narrated video of [Normal Maps and Tangent Frames in Elden Ring](../paper/ER_NORMAL_MAPS.md), built from the paper's
own figures. The narration is in `script.en.md`, organised by scene; each numbered segment (`S04-03`) becomes one
audio file.

## Prerequisites

- Python 3.11 or later; for rendering, the `websocket-client` package.
- Google Chrome, run headless to capture frames.
- ffmpeg and ffprobe, with libx264, AAC and libass (the `subtitles` filter).
- A network connection while rendering equation cards, which load KaTeX from a CDN.

## Steps

1. **Export the narration** for a speech tool:

   ```
   python docs/video/script.py en
   ```

   This writes `docs/video/out/tts/en/`: one `<segment>.txt` per segment, and `all.txt` with every segment as
   `<segment><tab><text>` on its own line.
2. **Generate the speech**, one audio file per segment, named after the segment, and put the files in
   `docs/video/audio/en/` (for example `docs/video/audio/en/S04-03.wav`). Any format ffprobe reads will do.
3. **Render** the video:

   ```
   python docs/video/make_video.py en
   ```

   This writes `docs/video/out/normal_maps.en.mp4` (1920 by 1080, 30 frames a second, subtitles burned in) and
   `normal_maps.en.srt`. Add `--draft` for a quick 960 by 540 render at 15 frames a second, or `--until 120` to
   render only the first 120 seconds (`normal_maps.en.until120.mp4`), a cheap way to check a change. Each segment's audio file
   sets its length; segments without one are timed from their word count, and the video is silent when no audio
   exists. The script reports missing files and files that match no segment. Rendered clips are cached in
   `docs/video/out/cache/`, so a second run renders only the visuals that changed.

## How it is built

- `script.py` reads the script; `timeline.py` lays the segments end to end, with a short pause between segments and
  a longer one between scenes, and ends on the references, held silent for 10 seconds.
- `scenes.py` builds one HTML page per visual from the paper and `docs/figures/`: figures, equations (KaTeX),
  tables, screenshots, title cards and the references. The figures and the paper are used as they are. The pages
  are dark, and Chrome is set to dark mode, so the figures use their own dark colours whatever the system's setting.
  Figures joined by ` + ` in the script are stacked top to bottom in one frame, as Fig. 3(a) over Fig. 3(b).
- Subtitles are burned in white on an opaque box, so the boxes of a two-line subtitle meet without a darker band.
- `chrome.py` drives headless Chrome to capture each page; animated figures are captured frame by frame, the rest
  once. `subtitles.py` writes the SRT, and `make_video.py` joins it all with ffmpeg.

`docs/video/audio/` and `docs/video/out/` are git-ignored: audio, exports, frames and videos stay out of the repository.
