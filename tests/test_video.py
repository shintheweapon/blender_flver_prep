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

import languages  # noqa: E402
import make_video  # noqa: E402
import scenes  # noqa: E402
import script  # noqa: E402
import subtitles  # noqa: E402
import timeline  # noqa: E402


def paper_text(lang="en"):
    with open(script.paper_path(lang), encoding="utf-8") as file:
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
        minutes = sum(s.words() for s in self.segments) / languages.language("en").rate
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
                               60 * segment.words() / languages.language("en").rate)


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
        text = subtitles.srt(subtitles.entries(self.cues[:3]))
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


class TestChinesePipeline(unittest.TestCase):
    """The pipeline builds Chinese pages and subtitles from the Chinese paper and figures."""

    SAMPLE = ("面部部件 FC_F_0000 沿加 Y 站立，面朝减 Z，左侧位于加 X。从正面看，x 向右、y 向上、z 指向屏幕内："
              "这是左手坐标系。其三角形的环绕顺序与之一致，前提是法线朝外。共 1,437 张贴图。")

    @classmethod
    def setUpClass(cls):
        cls.paper = scenes.paper_text("zh-CN")

    def test_the_chinese_paper_is_read(self):
        self.assertTrue(script.paper_path("zh-CN").endswith("ER_NORMAL_MAPS.zh-CN.md"))
        self.assertIn("## 参考文献", self.paper)

    def test_tables_keep_their_chinese_label(self):
        caption, rows = scenes.table(self.paper, "I")
        self.assertTrue(caption and len(rows) > 1)
        self.assertIn('<div class="caption">表 I<br>', scenes.content(("table", "I"), self.paper, "zh-CN")[0])
        self.assertTrue(script.visual_exists("table", "VI", self.paper, "zh-CN"))

    def test_references_keep_their_chinese_heading(self):
        self.assertEqual([n for n, _ in scenes.references(self.paper)], list(range(1, 10)))
        body = scenes.content(("references", ""), self.paper, "zh-CN")[0]
        self.assertIn("<h2>参考文献</h2>", body)
        self.assertIn("访问日期", body)

    def test_figures_are_the_chinese_ones_in_the_video_fonts(self):
        zh_text = scenes._zh_text()
        stack = zh_text.FONT_STACK.replace("sans-serif", ",".join(languages.CJK_FONTS) + ",sans-serif")
        names = {p for s in script.load("en") for v in [s.visual] + [g.show for g in s.segments if g.show]
                 if v[0] == "figure" for p in script.figure_files(v[1])}
        for name in sorted(names):
            with self.subTest(figure=name):
                self.assertTrue(script.visual_exists("figure", name, "", "zh-CN"))
                with open(os.path.join(script.FIGURES_DIR, name), encoding="utf-8") as file:
                    video = scenes.figure_text(file.read(), "zh-CN")
                with open(script.figure_path(name, "zh-CN"), encoding="utf-8") as file:
                    committed = file.read()
                self.assertEqual(video, committed.replace(zh_text.ZH_FONT_STACK, stack))

    def test_pages_lead_with_source_han_then_noto(self):
        page = scenes.page(script.Scene("S01", "问题", ("table", "I"), []), ("table", "I"), self.paper, "zh-CN")
        self.assertLess(page.index('"Source Han Sans SC"'), page.index('"Noto Sans SC"'))
        self.assertIn('<div class="heading">问题</div>', page)

    def test_subtitle_font_is_the_first_installed(self):
        self.assertEqual(languages.language("zh-CN").subtitle_fonts, ("Source Han Sans SC", "Noto Sans SC"))
        self.assertIn("FontName=Source Han Sans SC,", make_video.subtitle_style("Source Han Sans SC"))
        self.assertEqual(make_video.pick_font(("A", "B"), lambda f: f == "B"), "B")
        self.assertEqual(make_video.pick_font(("A", "B"), lambda f: True), "A")
        with self.assertRaises(LookupError):
            make_video.pick_font(("A", "B"), lambda f: False)

    def test_chinese_lines_fit_and_keep_every_character(self):
        lines = subtitles.wrap(self.SAMPLE)
        self.assertGreater(len(lines), 2)
        for line in lines:
            with self.subTest(line=line):
                self.assertLessEqual(subtitles.columns(line), subtitles.LINE_WIDTH)
                self.assertNotIn(line[0], subtitles.BREAK_AFTER)
        self.assertEqual("".join(lines).replace(" ", ""), self.SAMPLE.replace(" ", ""))
        for token in ("FC_F_0000", "1,437"):
            with self.subTest(token=token):
                self.assertTrue(any(token in line for line in lines))

    def test_chinese_counts_by_character(self):
        self.assertEqual(script.Segment("S01-01", "面朝减 Z，左侧").words(), 5 + 1)  # five characters and Z
        self.assertEqual(script.Segment("S01-01", "one two three").words(), 3)
        self.assertEqual(timeline.estimated_durations([script.Scene("S01", "t", ("title", "t"),
                                                       [script.Segment("S01-01", "面" * 260)])], "zh-CN"),
                         {"S01-01": 60.0})

    def test_an_unknown_language_is_refused(self):
        with self.assertRaises(KeyError):
            languages.language("xx")


class TestChineseScript(unittest.TestCase):
    """docs/video/script.zh-CN.md carries the English script's structure, in the Chinese paper's terms."""

    TERMS = ("切线空间法线", "副切线", "副切线符号", "法线贴图", "可积性检验", "偏导数", "左手坐标系", "镜像岛",
             "切线坐标系", "无镜像", "Z 轴镜像", "左手定则", "镜像变换", "DirectX 格式", "格式检验", "红色通道",
             "绿色通道", "翻转", "关于直线 U 等于 V 对称", "艾尔登法环")
    REJECTED = ("双切线", "次切线", "法线图", "左手系", "切空间", "可积分性", "反射", "DirectX 布局", "OpenGL 布局",
                "布局检验", "通道反转", "细节层级", "Elden Ring")
    HEDGES = ("未测试", "未确认", "很可能误判", "未作记录", "未在游戏内测试")

    @classmethod
    def setUpClass(cls):
        cls.en, cls.zh = script.load("en"), script.load("zh-CN")
        cls.segments = script.segments(cls.zh)
        cls.text = "".join(s.text for s in cls.segments)

    def test_same_scenes_segments_and_cues_as_the_english(self):
        self.assertEqual([s.ident for s in self.zh], [s.ident for s in self.en])
        self.assertEqual([s.ident for s in self.segments], [s.ident for s in script.segments(self.en)])
        self.assertEqual([s.show for s in self.segments], [s.show for s in script.segments(self.en)])
        # title cards carry translated text; every other visual is the same
        same = [s.visual if s.visual[0] != "title" else ("title",) for s in self.en]
        self.assertEqual([s.visual if s.visual[0] != "title" else ("title",) for s in self.zh], same)

    def test_every_visual_exists_in_chinese(self):
        text = paper_text("zh-CN")
        for scene in self.zh:
            for kind, name in [scene.visual] + [s.show for s in scene.segments if s.show]:
                with self.subTest(scene=scene.ident, visual=(kind, name)):
                    self.assertTrue(script.visual_exists(kind, name, text, "zh-CN"))

    def test_glossary_terms_are_used_and_rejected_ones_are_not(self):
        for term in self.TERMS:
            with self.subTest(term=term):
                self.assertIn(term, self.text)
        for variant in self.REJECTED:
            with self.subTest(variant=variant):
                self.assertNotIn(variant, self.text)

    def test_channels_are_named_as_channels(self):
        from test_paper_zh import BARE_CHANNEL
        self.assertEqual(re.findall(BARE_CHANNEL, self.text), [])

    def test_untested_claims_stay_marked(self):
        for phrase in self.HEDGES:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    def test_handedness_reasons_are_given(self):
        s04_04 = next(s.text for s in self.segments if s.ident == "S04-04")
        for reason in ("模组社区长期认为", "两种手性", "这两点本文均未测试"):
            with self.subTest(reason=reason):
                self.assertIn(reason, s04_04)

    def test_no_dash_punctuation(self):
        for segment in self.segments:
            with self.subTest(segment=segment.ident):
                self.assertNotRegex(segment.text, r"[–—]|--| - ")

    def test_length_is_12_to_20_minutes(self):
        minutes = sum(s.words() for s in self.segments) / languages.language("zh-CN").rate
        self.assertGreaterEqual(minutes, 12)
        self.assertLessEqual(minutes, 20)


class TestWordBreaks(unittest.TestCase):
    """Chinese lines break between the words a splitter gives, never inside one (no jieba is imported)."""

    TEXT = "导入艾尔登法环的自制网格，法线贴图可能按错误的方向着色：凸起的细节看起来是凹陷的，或者像是从侧面照亮。"
    WORDS = ["导入", "艾尔登法环", "的", "自制", "网格", "，", "法线", "贴图", "可能", "按", "错误", "的", "方向",
             "着色", "：", "凸起", "的", "细节", "看起来", "是", "凹陷", "的", "，", "或者", "像是", "从", "侧面",
             "照亮", "。"]

    def split(self, run):
        # a fake splitter: the words above, in order, for any run of this text
        out, rest = [], run
        for word in self.WORDS:
            if rest.startswith(word):
                out.append(word)
                rest = rest[len(word):]
        return out + list(rest)

    def test_no_line_breaks_inside_a_word(self):
        lines = subtitles.wrap(self.TEXT, split=self.split)
        joined = "".join(lines)
        self.assertEqual(joined, self.TEXT)
        cuts, position = set(), 0
        for line in lines[:-1]:
            position += len(line)
            cuts.add(position)
        edges, position = set(), 0
        for word in self.WORDS:
            position += len(word)
            edges.add(position)
        self.assertLessEqual(cuts, edges)
        for line in lines:
            with self.subTest(line=line):
                self.assertLessEqual(subtitles.columns(line), subtitles.LINE_WIDTH)
                self.assertNotIn(line[0], subtitles.BREAK_AFTER)

    def test_a_word_wider_than_a_line_falls_back_to_characters(self):
        self.assertEqual(subtitles.units("一二三四", width=4, split=lambda run: [run]), ["一", "二", "三", "四"])
        self.assertEqual(subtitles.units("一二", width=4, split=lambda run: [run]), ["一二"])

    def test_english_is_unchanged_by_a_splitter(self):
        for segment in script.segments(script.load("en")):
            with self.subTest(segment=segment.ident):
                self.assertEqual(subtitles.wrap(segment.text, split=self.split), subtitles.wrap(segment.text))

    def test_glossary_terms_are_read_for_the_splitter(self):
        terms = subtitles.glossary_terms()
        for term in ("艾尔登法环", "切线空间法线", "副切线符号", "可积性检验", "通道变换"):
            with self.subTest(term=term):
                self.assertIn(term, terms)
        self.assertNotIn("中文", terms)

    def test_chinese_names_jieba_and_english_no_splitter(self):
        self.assertEqual(languages.language("zh-CN").words, "jieba")
        self.assertIsNone(languages.language("en").words)
        self.assertIs(make_video.WORD_SPLITTERS["jieba"], subtitles.jieba_words)


class TestSubtitleTiming(unittest.TestCase):
    """Group boundaries move to pauses in the speech, and a partial render keeps each segment's own timing."""

    LONG = "word " * 30  # four lines at 42 columns: two groups, one boundary

    def cue(self, start=10.0, end=20.0, ident="S01-01"):
        return timeline.Cue(ident, "S01", self.LONG.strip(), start, end)

    def test_a_boundary_moves_to_a_pause_within_reach(self):
        [(_, first_end, _), (second_start, _, _)] = subtitles.entries([self.cue()], pauses={"S01-01": [(5.6, 6.0)]})
        self.assertAlmostEqual(first_end, 15.8)
        self.assertAlmostEqual(second_start, 15.8)

    def test_a_boundary_without_a_pause_in_reach_keeps_its_time(self):
        plain = subtitles.entries([self.cue()])
        far = subtitles.entries([self.cue()], pauses={"S01-01": [(1.0, 1.4)]})
        self.assertEqual(far, plain)

    def test_pauses_at_a_segments_ends_are_ignored(self):
        self.assertEqual(subtitles.snap([1.0], [(0.0, 0.2), (9.9, 10.0)], 0.0, 10.0), [1.0])

    def test_boundaries_stay_in_order(self):
        moved = subtitles.snap([3.0, 3.5, 6.0], [(2.4, 2.6), (6.4, 6.6)], 0.0, 10.0)
        self.assertEqual(moved, sorted(moved))
        self.assertAlmostEqual(moved[0], 2.5)

    def test_clip_keeps_each_entrys_own_timing(self):
        found = subtitles.entries([self.cue()])
        clipped = subtitles.clip(found, 16.0)
        self.assertEqual(clipped[0], found[0])
        self.assertEqual(clipped[-1][1], min(found[len(clipped) - 1][1], 16.0))
        self.assertTrue(all(start < 16.0 for start, _, _ in clipped))
        self.assertEqual(subtitles.clip(found, None), found)

    def test_ffmpeg_silences_are_parsed(self):
        log = ("[silencedetect @ 0x1] silence_start: 0\n[silencedetect @ 0x1] silence_end: 0.31 | silence_duration: "
               "0.31\n[silencedetect @ 0x1] silence_start: 4.52\n[silencedetect @ 0x1] silence_end: 5.1 | "
               "silence_duration: 0.58\n[silencedetect @ 0x1] silence_start: 9.8\n")
        self.assertEqual(timeline.parse_silences(log), [(0.0, 0.31), (4.52, 5.1)])


if __name__ == "__main__":
    unittest.main()
