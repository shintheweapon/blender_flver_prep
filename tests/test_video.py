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

import script  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
