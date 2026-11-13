# Tests for the paper's figures in Chinese, docs/figures/zh_text.py: each English figure the paper shows has a
# Chinese file, every string with words is translated (names such as DirectX stay), and animations are kept.

import html
import os
import re
import sys
import unittest

FIGURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "figures")
if FIGURES_DIR not in sys.path:
    sys.path.insert(0, FIGURES_DIR)

import make_figures  # noqa: E402
import zh_text  # noqa: E402

# Words that stay in Latin letters in the Chinese figures: names, file-name prefixes and Blender's setting name
KEPT = {"DirectX", "OpenGL", "Blender", "FLVER", "FBX", "MikkTSpace", "ER", "Tangents", "Tangent", "Space", "Alpha",
        "FG", "AA", "FC", "HR", "HA", "WP", "BD", "HD", "LG", "AM", "UV"}


def texts(svg):
    """The character data of every text, title and description in an SVG."""
    found = []
    for _, body in re.findall(r"<(text|title|desc)\b[^>]*>(.*?)</\1>", svg, re.S):
        found += [html.unescape(p).strip() for p in re.split(r"<[^>]+>", body) if p.strip()]
    return found


class TestChineseFigures(unittest.TestCase):
    """The paper's figures in Chinese."""

    @classmethod
    def setUpClass(cls):
        cls.figures = make_figures.build_all()

    def test_every_paper_figure_has_a_chinese_file(self):
        for name in zh_text.PAPER_FIGURES:
            with self.subTest(name=name):
                self.assertIn(zh_text.zh_name(name), self.figures)

    def test_every_english_string_with_words_is_in_the_catalogue(self):
        for name in zh_text.PAPER_FIGURES:
            for text in texts(self.figures[name]):
                if re.search(r"[A-Za-z]{2,}", text) and set(re.findall(r"[A-Za-z]{2,}", text)) - KEPT:
                    with self.subTest(name=name, text=text):
                        self.assertIn(text, zh_text.ZH)

    def test_no_english_word_is_left_in_the_chinese_figures(self):
        for name in zh_text.PAPER_FIGURES:
            zh = zh_text.zh_name(name)
            for text in texts(self.figures[zh]):
                with self.subTest(name=zh, text=text):
                    self.assertEqual(set(re.findall(r"[A-Za-z]{3,}", text)) - KEPT, set())

    def test_animations_are_kept(self):
        for name in ("paper_axis_swap_animated.svg", "paper_dome_tilts.svg"):
            with self.subTest(name=name):
                english, chinese = self.figures[name], self.figures[zh_text.zh_name(name)]
                self.assertEqual(chinese.count("<animate"), english.count("<animate"))
                self.assertEqual(chinese.count("@keyframes"), english.count("@keyframes"))
                self.assertGreater(chinese.count("<animate") + chinese.count("@keyframes"), 0)

    def test_only_text_changes(self):
        # with the text and the font stack put back, a Chinese figure is its English figure
        for name in zh_text.PAPER_FIGURES:
            english, chinese = self.figures[name], self.figures[zh_text.zh_name(name)]
            strip = re.compile(r"(<(?:text|title|desc)\b[^>]*>)(.*?)(</(?:text|title|desc)>)", re.S)
            skeleton = lambda svg: strip.sub(lambda m: m.group(1) + re.sub(r"[^<>]+(?=<|$)", "", m.group(2))
                                             + m.group(3), svg)
            with self.subTest(name=name):
                self.assertEqual(skeleton(chinese).replace(zh_text.ZH_FONT_STACK, zh_text.FONT_STACK),
                                 skeleton(english))

    def test_channels_are_named_as_channels(self):
        # as in the paper; 绿色 T and 红色 W name the colours of the drawn arrows
        bare = (r"(?:红色|绿色|蓝色)(?!通道|(?:和|与)(?:红色|绿色|蓝色)通道|(?:和|与) Alpha 通道| [TW])"
                r"|Alpha(?! 通道)")
        for value in zh_text.ZH.values():
            with self.subTest(value=value[:30]):
                self.assertEqual(re.findall(bare, value), [])

    def test_reflections_are_not_named_as_light(self):
        # 反射 reads as the reflection of light: 镜像变换, or 关于 U = V 对称
        for value in zh_text.ZH.values():
            with self.subTest(value=value[:30]):
                self.assertNotIn("反射", value)

    def test_graphics_terms_are_the_chinese_ones(self):
        # DirectX 格式 rather than 布局, and a channel is 翻转, as in Chinese graphics writing
        for value in zh_text.ZH.values():
            with self.subTest(value=value[:30]):
                self.assertNotIn("布局", value)
                self.assertNotIn("通道反转", value)

    def test_chinese_fonts_are_added(self):
        for name in zh_text.PAPER_FIGURES:
            with self.subTest(name=name):
                self.assertIn("Microsoft YaHei", self.figures[zh_text.zh_name(name)])


if __name__ == "__main__":
    unittest.main()
