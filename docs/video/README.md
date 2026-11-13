# The paper's video

A narrated video of [Normal Maps and Tangent Frames in Elden Ring](../paper/ER_NORMAL_MAPS.md), built from the paper's
own figures. The narration is in `script.en.md`, organised by scene; each numbered segment (`S04-03`) becomes one
audio file.

## Prerequisites

- Python 3.11 or later; for rendering, the `websocket-client` package, and for the Chinese video, `jieba`.
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

## The Chinese video

`script.zh-CN.md` is the narration in Simplified Chinese, with the English script's scenes, segment IDs and visuals.
The same steps with `zh-CN` in place of `en` build it:

```
python docs/video/script.py zh-CN
python docs/video/make_video.py zh-CN
```

The audio goes in `docs/video/audio/zh-CN/`, and the video is written to `docs/video/out/normal_maps.zh-CN.mp4`. Its
pages are built from the Chinese paper, its tables, its references and the Chinese figures (`docs/figures/zh_text.py`).
Pages and subtitles use Source Han Sans SC, or Noto Sans SC where it is not installed; the render prints the font it
chose. Chinese subtitle lines hold 21 characters and break between words, found with jieba and the glossary's
terms (`docs/paper/glossary.zh-CN.md`), preferably after punctuation. What differs per language is in `languages.py`.

## How it is built

- `script.py` reads the script; `timeline.py` lays the segments end to end, with a short pause between segments and
  a longer one between scenes, and ends on the references, held silent for 10 seconds.
- `scenes.py` builds one HTML page per visual from the paper and `docs/figures/`: figures, equations (KaTeX),
  tables, screenshots, title cards and the references. The figures and the paper are used as they are. The pages
  are dark, and Chrome is set to dark mode, so the figures use their own dark colours whatever the system's setting.
  Figures joined by ` + ` in the script are stacked top to bottom in one frame, as Fig. 3(a) over Fig. 3(b).
- Subtitles are burned in white on an opaque box, so the boxes of a two-line subtitle meet without a darker band.
  English subtitles change at sentence ends, where the narration pauses: whole sentences share a subtitle while
  they fit in two lines, and a longer sentence is cut into even parts, at a comma near the cut where one is; the
  two lines of an English subtitle are about equal in length.
  Chinese subtitles fill two lines at a time. Each segment's time is shared between its subtitles by their length,
  and each change of subtitle then moves to the nearest pause in the segment's audio, found with ffmpeg's
  `silencedetect`, within 1.5 seconds. A partial render (`--until`) times the subtitles on the whole video and then
  cuts them, so they keep in step.
- `chrome.py` drives headless Chrome to capture each page; animated figures are captured frame by frame, the rest
  once. `subtitles.py` writes the SRT, and `make_video.py` joins it all with ffmpeg.

`docs/video/audio/` and `docs/video/out/` are git-ignored: audio, exports, frames and videos stay out of the repository.
