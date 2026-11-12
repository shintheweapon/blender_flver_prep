# Tests for the video's narration, docs/video/script.en.md and docs/video/script.py: the script parses, its segments
# are numbered in order, every visual it names exists, and it is 12 to 20 minutes long. No browser code is imported.

import os
import re
import sys
import tempfile
import unittest

VIDEO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "video")
if VIDEO_DIR not in sys.path:
    sys.path.insert(0, VIDEO_DIR)

import make_video  # noqa: E402
import scenes  # noqa: E402
import script  # noqa: E402
import subtitles  # noqa: E402
import timeline  # noqa: E402


def paper_text():
    with open(script.PAPER, encoding="utf-8") as file:
        return file.read()


class TestScriptFormat(unittest.TestCase):
    """The parser reads scenes, visuals, segments and show cues."""

    SAMPLE = ("<!-- a note -->\n## S01 First\n\nVisual: title Hello\n\n**S01-01**\nOne line\nand another.\n\n"
              "**S01-02**\n{show: figure tangent_frame.svg}\nShown.\n\n## S02 Second\n\nVisual: equation 1\n\n"
              "**S02-01**\nLast.\n")

    def test_scenes_and_segments(self):
        scenes = script.parse(self.SAMPLE)
        self.assertEqual([s.ident for s in scenes], ["S01", "S02"])
        self.assertEqual(scenes[0].visual, ("title", "Hello"))
        first, second = scenes[0].segments
        self.assertEqual((first.ident, first.text, first.show), ("S01-01", "One line and another.", None))
        self.assertEqual((second.text, second.show), ("Shown.", ("figure", "tangent_frame.svg")))

    def test_a_scene_without_a_visual_is_refused(self):
        with self.assertRaises(ValueError):
            script.parse("## S01 First\n\n**S01-01**\nText.\n")

    def test_a_references_scene_has_no_segments(self):
        [scene] = script.parse("## S01 References\n\nVisual: references\n")
        self.assertEqual((scene.visual, scene.segments), (("references", ""), []))
        with self.assertRaises(ValueError):
            script.parse("## S01 References\n\nVisual: references\n\n**S01-01**\nText.\n")

    def test_only_a_silent_scene_may_have_no_segments(self):
        with self.assertRaises(ValueError):
            script.parse("## S01 Empty\n\nVisual: title Empty\n")

    def test_export_writes_one_file_per_segment_and_a_combined_file(self):
        scenes = script.parse(self.SAMPLE)
        with tempfile.TemporaryDirectory() as folder:
            script.export(scenes, out_dir=folder)
            self.assertEqual(sorted(os.listdir(folder)), ["S01-01.txt", "S01-02.txt", "S02-01.txt", "all.txt"])
            with open(os.path.join(folder, "all.txt"), encoding="utf-8") as file:
                self.assertEqual(file.read().splitlines()[1], "S01-02\tShown.")


class TestEnglishScript(unittest.TestCase):
    """The English script is complete and consistent."""

    @classmethod
    def setUpClass(cls):
        cls.scenes = script.load("en")
        cls.segments = script.segments(cls.scenes)

    def test_scene_ids_count_up_from_one(self):
        self.assertEqual([s.ident for s in self.scenes], [f"S{i:02d}" for i in range(1, len(self.scenes) + 1)])

    def test_segment_ids_count_up_within_each_scene(self):
        for scene in self.scenes:
            with self.subTest(scene=scene.ident):
                self.assertEqual([s.ident for s in scene.segments],
                                 [f"{scene.ident}-{i:02d}" for i in range(1, len(scene.segments) + 1)])

    def test_every_segment_has_text_without_markup(self):
        for segment in self.segments:
            with self.subTest(segment=segment.ident):
                self.assertTrue(segment.text)
                self.assertNotRegex(segment.text, r"[{}*$\\]|\(\d+\)")

    def test_every_visual_exists(self):
        text = paper_text()
        for scene in self.scenes:
            visuals = [scene.visual] + [s.show for s in scene.segments if s.show]
            for kind, name in visuals:
                with self.subTest(scene=scene.ident, visual=(kind, name)):
                    self.assertIn(kind, script.KINDS)
                    self.assertTrue(script.visual_exists(kind, name, text))

    def test_the_video_ends_on_the_references(self):
        self.assertEqual(self.scenes[-1].visual[0], "references")
        self.assertEqual([s for s in self.scenes if s.visual[0] in script.SILENT_KINDS], [self.scenes[-1]])

    def test_length_is_12_to_20_minutes(self):
        minutes = sum(s.words() for s in self.segments) / script.WORDS_PER_MINUTE
        self.assertGreaterEqual(minutes, 12)
        self.assertLessEqual(minutes, 20)

    def test_no_dash_punctuation(self):
        for segment in self.segments:
            with self.subTest(segment=segment.ident):
                self.assertNotRegex(segment.text, r"[–—]|--| - ")

    def test_untested_claims_stay_marked(self):
        text = " ".join(s.text for s in self.segments)
        for phrase in ("That was not tested here", "unconfirmed for Elden Ring", "not tested in game",
                       "was not recorded", "likely misreads"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


class TestTimeline(unittest.TestCase):
    """The narration and the visuals are laid out end to end, ending on the silent references."""

    @classmethod
    def setUpClass(cls):
        cls.scenes = script.load("en")
        cls.cues, cls.spans, cls.total = timeline.build(cls.scenes, timeline.estimated_durations(cls.scenes))

    def test_every_segment_has_one_cue_in_order(self):
        self.assertEqual([c.ident for c in self.cues], [s.ident for s in script.segments(self.scenes)])
        for before, after in zip(self.cues, self.cues[1:]):
            self.assertGreater(after.start, before.end)

    def test_spans_join_without_gaps_from_zero_to_the_end(self):
        self.assertEqual(self.spans[0].start, 0.0)
        for before, after in zip(self.spans, self.spans[1:]):
            self.assertEqual(before.end, after.start)
        self.assertEqual(self.spans[-1].end, self.total)

    def test_every_cue_falls_within_its_scene_spans(self):
        for cue in self.cues:
            own = [s for s in self.spans if s.scene.ident == cue.scene]
            self.assertGreaterEqual(cue.start, own[0].start)
            self.assertLessEqual(cue.end, own[-1].end)

    def test_the_video_ends_with_a_silent_references_hold(self):
        last = self.spans[-1]
        self.assertEqual(last.visual[0], "references")
        self.assertAlmostEqual(last.duration, script.REFERENCES_HOLD)
        self.assertLessEqual(self.cues[-1].end, last.start)

    def test_a_show_cue_switches_the_visual_at_its_segment(self):
        shown = {s.ident: s.show for s in script.segments(self.scenes) if s.show}
        starts = {c.ident: c.start for c in self.cues}
        for ident, visual in shown.items():
            with self.subTest(segment=ident):
                [span] = [s for s in self.spans if s.start == starts[ident]]
                self.assertEqual(span.visual, visual)

    def test_estimated_durations_follow_the_word_count(self):
        segment = script.segments(self.scenes)[0]
        self.assertAlmostEqual(timeline.estimated_durations(self.scenes)[segment.ident],
                               60 * segment.words() / script.WORDS_PER_MINUTE)


class TestSubtitles(unittest.TestCase):
    """The SRT is well formed, its lines fit, and nothing is shown during the silent hold."""

    @classmethod
    def setUpClass(cls):
        found = script.load("en")
        cls.cues, cls.spans, _ = timeline.build(found, timeline.estimated_durations(found))
        cls.entries = subtitles.entries(cls.cues)

    def test_wrap_keeps_lines_within_the_width(self):
        self.assertEqual(subtitles.wrap("one two three four", 9), ["one two", "three", "four"])
        self.assertEqual(subtitles.wrap("averyveryverylongword x", 5), ["averyveryverylongword", "x"])

    def test_lines_fit_and_entries_hold_at_most_two(self):
        for start, end, lines in self.entries:
            self.assertLessEqual(len(lines), subtitles.MAX_LINES)
            for line in lines:
                self.assertTrue(len(line) <= subtitles.LINE_WIDTH or " " not in line, line)

    def test_entries_keep_every_word_in_order(self):
        words = " ".join(" ".join(lines) for _, _, lines in self.entries).split()
        self.assertEqual(words, " ".join(c.text for c in self.cues).split())

    def test_entries_are_in_time_order_within_their_cues(self):
        for (s1, e1, _), (s2, e2, _) in zip(self.entries, self.entries[1:]):
            self.assertLess(s1, e1)
            self.assertLessEqual(e1, s2 + 1e-9)

    def test_no_subtitle_during_the_references(self):
        hold = self.spans[-1]
        self.assertTrue(all(end <= hold.start + 1e-9 for _, end, _ in self.entries))

    def test_srt_blocks_are_numbered_and_timed(self):
        text = subtitles.srt(self.cues[:3])
        blocks = text.strip().split("\n\n")
        for number, block in enumerate(blocks, 1):
            lines = block.splitlines()
            self.assertEqual(lines[0], str(number))
            self.assertRegex(lines[1], r"^\d\d:\d\d:\d\d,\d{3} --> \d\d:\d\d:\d\d,\d{3}$")
        self.assertEqual(subtitles.timestamp(3725.5), "01:02:05,500")


class TestScenes(unittest.TestCase):
    """Every visual builds a page, and the references card is the paper's list."""

    @classmethod
    def setUpClass(cls):
        cls.paper = scenes.paper_text()
        cls.scenes = script.load("en")
        cls.spans = timeline.build(cls.scenes, timeline.estimated_durations(cls.scenes))[1]

    def test_every_span_builds_a_page_with_the_two_hooks(self):
        for span in self.spans:
            with self.subTest(scene=span.scene.ident, visual=span.visual):
                page = scenes.page(span.scene, span.visual, self.paper)
                self.assertIn("window.ready = prepare();", page)
                self.assertIn("window.setTime = async function", page)

    def test_references_are_the_papers_in_order(self):
        refs = scenes.references(self.paper)
        section = self.paper[self.paper.index("\n## References\n"):]
        self.assertEqual([n for n, _ in refs], list(range(1, len(re.findall(r"^\[\d+\] ", section, re.M)) + 1)))
        self.assertTrue(refs[0][1].startswith('soulsmods, "SoulsFormatsNEXT,"'))

    def test_references_card_renders_marks_not_symbols(self):
        body = scenes.content(("references", ""), self.paper)[0]
        text = re.sub(r"<[^>]+>", "", body)
        self.assertNotIn("`", text)
        self.assertNotRegex(text, r"\*\w")
        self.assertIn("<i>FBX SDK 2020.2.1</i>", body)
        self.assertEqual(body.count("<p>["), len(scenes.references(self.paper)))

    def test_equations_and_tables_are_read_from_the_paper(self):
        self.assertIn(r"\tag{19}", scenes.equation_tex(self.paper, "19"))
        caption, rows = scenes.table(self.paper, "V")
        self.assertEqual(caption, "WORKED EXAMPLE FOR ONE TRIANGLE")
        self.assertEqual(rows[0], ["Quantity", "Value"])
        with self.assertRaises(KeyError):
            scenes.table(self.paper, "XX")

    def test_only_animated_figures_move(self):
        self.assertTrue(scenes.moves(("figure", "paper_axis_swap_animated.svg")))
        self.assertTrue(scenes.moves(("figure", "paper_dome_tilts.svg")))
        self.assertFalse(scenes.moves(("figure", "paper_axis_swap.svg")))
        self.assertFalse(scenes.moves(("equation", "1")))


class TestLook(unittest.TestCase):
    """Dark pages, subtitles in an opaque box, and a stage clear of the subtitles."""

    @classmethod
    def setUpClass(cls):
        cls.paper = scenes.paper_text()
        found = script.load("en")
        cls.spans = timeline.build(found, timeline.estimated_durations(found))[1]

    def test_every_page_is_dark(self):
        for span in self.spans:
            with self.subTest(scene=span.scene.ident, visual=span.visual):
                page = scenes.page(span.scene, span.visual, self.paper)
                self.assertIn("color-scheme: dark", page)
                self.assertIn(f"background: {scenes.BACKGROUND};", page)
                self.assertNotRegex(page.lower(), r"background:\s*#fff")

    def test_subtitles_are_larger_in_an_opaque_box(self):
        style = dict(item.split("=", 1) for item in make_video.SUBTITLE_STYLE.split(","))
        self.assertEqual(style["FontSize"], "13.2")
        self.assertEqual(style["BorderStyle"], "3")
        self.assertTrue(style["OutlineColour"].startswith("&H00"), "the box must be opaque")

    def test_the_stage_ends_above_the_subtitles(self):
        self.assertLessEqual(scenes.STAGE_TOP + scenes.STAGE_HEIGHT, make_video.SUBTITLE_TOP)


class TestStackedFigures(unittest.TestCase):
    """Figures joined by " + " are drawn top to bottom in one frame, as Fig. 3(a) over Fig. 3(b)."""

    STACK = "paper_axis_swap_animated.svg + paper_axis_swap.svg"

    def test_a_stack_exists_when_every_file_does(self):
        self.assertEqual(script.figure_files(self.STACK), ["paper_axis_swap_animated.svg", "paper_axis_swap.svg"])
        self.assertTrue(script.visual_exists("figure", self.STACK, ""))
        self.assertFalse(script.visual_exists("figure", "paper_axis_swap.svg + missing.svg", ""))

    def test_the_stack_holds_both_figures_in_order(self):
        body = scenes.content(("figure", self.STACK), scenes.paper_text())[0]
        self.assertTrue(body.startswith('<div class="stack">'))
        self.assertEqual(body.count("<svg"), 2)
        self.assertLess(body.index("<animate"), body.index("<svg", body.index("<svg") + 1))

    def test_a_stack_with_an_animated_figure_moves(self):
        self.assertTrue(scenes.moves(("figure", self.STACK)))

    def test_s04_06_shows_the_panels_below_the_animation(self):
        [segment] = [s for s in script.segments(script.load("en")) if s.ident == "S04-06"]
        self.assertEqual(segment.show, ("figure", self.STACK))
        self.assertIn("The three panels below", segment.text)


class TestPartialRender(unittest.TestCase):
    """A render of the first seconds keeps only what starts before them, cut to fit."""

    @classmethod
    def setUpClass(cls):
        found = script.load("en")
        cls.cues, cls.spans, cls.total = timeline.build(found, timeline.estimated_durations(found))

    def test_nothing_is_cut_without_a_limit(self):
        spans, cues, total = make_video.until_spans(self.spans, self.cues, None)
        self.assertEqual((len(spans), len(cues), total), (len(self.spans), len(self.cues), self.total))

    def test_spans_and_cues_end_at_the_limit(self):
        spans, cues, total = make_video.until_spans(self.spans, self.cues, 120)
        self.assertEqual(total, 120)
        self.assertEqual(spans[-1].end, 120)
        self.assertTrue(all(s.start < 120 for s in spans) and all(c.end <= 120 for c in cues))
        self.assertEqual(len(spans), sum(s.start < 120 for s in self.spans))
        self.assertEqual(sum(make_video.frame_counts(spans, 30)), 120 * 30)


if __name__ == "__main__":
    unittest.main()
