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
3. **Render** the video (to come with the renderer).

`docs/video/audio/` and `docs/video/out/` are git-ignored: audio, exports, frames and videos stay out of the repository.
