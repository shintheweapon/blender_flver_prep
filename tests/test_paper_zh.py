# Tests for docs/paper/ER_NORMAL_MAPS.zh-CN.md, the Simplified Chinese paper: it carries the English paper's equations,
# tables, figures, citations, references and counts unchanged, in the same order, and uses the glossary's terms.

import os
import re
import sys
import unittest

PAPER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "paper")
FIGURES_DIR = os.path.join(os.path.dirname(PAPER_DIR), "figures")
ENGLISH = os.path.join(PAPER_DIR, "ER_NORMAL_MAPS.md")
CHINESE = os.path.join(PAPER_DIR, "ER_NORMAL_MAPS.zh-CN.md")
REFERENCES = {"en": "## References", "zh": "## 参考文献"}
B = "\\"
# a channel word without 通道, alone or as the first of two channels sharing it
BARE_CHANNEL = r"(?:红色|绿色|蓝色)(?!通道|(?:和|与)(?:红色|绿色|蓝色)通道|(?:和|与) Alpha 通道)|Alpha(?! 通道)"


def read(path):
    with open(path, encoding="utf-8") as file:
        return file.read()


def equations(text):
    """The displayed equations, with the words inside \\text{...} left out (they are translated)."""
    blocks = re.findall(r"^\$\$\n(.*?)\n\$\$$", text, flags=re.M | re.S)
    return [re.sub(re.escape(B + "text{") + r"[^}]*\}", B + "text{}", block) for block in blocks]


def tables(text):
    """Each table's numeral and, per body row, its numbers and maths in order (the words are translated)."""
    found = []
    for numeral, body in re.findall(r'<p align="center">(?:TABLE|表) ([IVX]+)<br>.*?</p>\n\n((?:\|.*\n)+)', text):
        rows = body.splitlines()[2:]
        # sorted: a translated row may name its equation number before its symbol
        found.append((numeral, [sorted(re.findall(r"\$[^$]+\$|\d[\d.,]*%?", row)) for row in rows]))
    return found


def without_maths(text):
    """The text with display and inline maths removed, where a minus sign is not punctuation."""
    text = re.sub(r"^\$\$\n.*?\n\$\$$", "", text, flags=re.M | re.S)
    return re.sub(r"\$[^$\n]+\$", "", text)


def citations(text, heading):
    """The reference numbers in order of first citation, in the body."""
    order = []
    for group in re.findall(r"\[(\d+(?:\]\s*,\s*\[\d+)*)\]", text.split(heading)[0]):
        for number in re.findall(r"\d+", group):
            if number not in order:
                order.append(number)
    return order


def references(text, heading):
    """The reference list as text."""
    return text.split(heading)[1].strip()


class TestChinesePaper(unittest.TestCase):
    """The Chinese paper matches the English one wherever it carries no words."""

    @classmethod
    def setUpClass(cls):
        cls.en, cls.zh = read(ENGLISH), read(CHINESE)

    def test_the_same_equations_in_the_same_order(self):
        self.assertEqual(equations(self.zh), equations(self.en))
        self.assertEqual(len(equations(self.zh)), 21)

    def test_every_displayed_equation_is_followed_by_words(self):
        for after in re.findall(r"^\$\$$\n\n(.*)", self.zh, flags=re.M):
            if after.startswith("*"):
                with self.subTest(line=after[:30]):
                    self.assertTrue(after.startswith("*文字表述：*"))
        self.assertEqual(self.zh.count("*文字表述：*"), self.en.count("*In words:*"))

    def test_the_same_tables_with_the_same_numbers(self):
        self.assertEqual(tables(self.zh), tables(self.en))
        self.assertEqual([numeral for numeral, _ in tables(self.zh)], ["I", "II", "III", "IV", "V", "VI"])

    def test_the_same_figures_in_order_each_with_its_caption(self):
        def images(text):
            return [os.path.basename(p).replace(".zh.svg", ".svg") for p in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)]
        self.assertEqual(images(self.zh), images(self.en))
        for path in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", self.zh):
            with self.subTest(image=path):
                self.assertTrue(os.path.isfile(os.path.normpath(os.path.join(PAPER_DIR, path))))
                if path.endswith(".svg"):
                    self.assertTrue(path.endswith(".zh.svg"))
        captions = re.findall(r"^图 (\d+)\. ", self.zh, flags=re.M)
        self.assertEqual(captions, [str(n) for n in range(1, 12)])

    def test_the_same_citations_in_the_same_order(self):
        self.assertEqual(citations(self.zh, REFERENCES["zh"]), citations(self.en, REFERENCES["en"]))

    def test_references_are_the_english_ones_with_chinese_access_dates(self):
        english = references(self.en, REFERENCES["en"])
        english = re.sub(r"Accessed: (\d+) Nov\. 2026\.", lambda m: f"访问日期：2026年11月{m.group(1)}日。", english)
        self.assertEqual(" ".join(references(self.zh, REFERENCES["zh"]).split()), " ".join(english.split()))

    def test_the_counts_are_kept(self):
        for number in re.findall(r"\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?%", self.en.split(REFERENCES["en"])[0]):
            with self.subTest(number=number):
                self.assertIn(number, self.zh)

    def test_the_part_and_mesh_names_are_kept(self):
        for name in set(re.findall(r"\b[A-Z]{2}_[A-Z]_\d{4}\b", self.en)):
            with self.subTest(name=name):
                self.assertIn(name, self.zh)

    def test_the_papers_link_each_other(self):
        self.assertIn("[简体中文](ER_NORMAL_MAPS.zh-CN.md)", self.en)
        self.assertIn("[English](ER_NORMAL_MAPS.md)", self.zh)


class TestChineseStyle(unittest.TestCase):
    """The Chinese paper keeps the English paper's conventions in Chinese form."""

    @classmethod
    def setUpClass(cls):
        cls.zh = read(CHINESE)
        cls.body = cls.zh.split(REFERENCES["zh"])[0]

    def test_glossary_terms_are_used(self):
        for term in ("切线空间法线", "副切线", "副切线符号", "法线贴图", "可积性检验", "偏导数", "左手坐标系",
                     "镜像岛", "非镜像岛", "切线坐标系", "无镜像", "Z 轴镜像", "左手定则", "镜像变换",
                     "关于直线 U = V 对称"):
            with self.subTest(term=term):
                self.assertIn(term, self.body)

    def test_rejected_variants_are_not_used(self):
        for variant in ("双切线", "次切线", "法线图", "左手系", "切空间", "可积分性", "反射"):
            with self.subTest(variant=variant):
                self.assertNotIn(variant, self.body)

    def test_games_are_named_in_chinese(self):
        # the English name only once, in brackets at first use
        self.assertEqual(self.body.count("Elden Ring"), 1)
        self.assertIn("艾尔登法环（Elden Ring）", self.body)
        for name in ("黑暗之魂 3（Dark Souls 3）", "只狼（Sekiro）", "装甲核心 6（Armored Core 6）", "艾尔登法环 黑夜君临（Nightreign）"):
            with self.subTest(name=name):
                self.assertIn(name, self.body)

    def test_channels_are_named_as_channels(self):
        # 红色 alone reads as a colour: each channel takes 通道, shared by two named together
        self.assertEqual(re.findall(BARE_CHANNEL, self.body), [])

    def test_untested_claims_stay_marked(self):
        for phrase in ("未测试", "未确认", "可能误判", "未作记录", "未在游戏内测试"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.body)

    def test_test_sections_keep_their_lead_ins(self):
        for label in ("**问题。**", "**意义。**", "**检验方法。**", "**结果。**", "**对实现的影响。**"):
            with self.subTest(label=label):
                self.assertGreaterEqual(self.body.count(label), 6)

    def test_tables_have_chinese_captions_above(self):
        self.assertEqual(re.findall(r'<p align="center">表 ([IVX]+)<br>', self.zh), ["I", "II", "III", "IV", "V", "VI"])

    def test_no_dash_punctuation(self):
        # a hyphen with a space on each side, after text (a list bullet starts its line)
        self.assertNotRegex(without_maths(self.body), r"[–—]|——| -- |(?<=\S) - ")

    def test_names_no_tool_setting_or_file_in_the_body(self):
        body = self.body.split("## 致谢")[0]
        for pattern in (r"FbxImporter", r"FLVER Prep", r"Transform", r"docs/", r"\b[\w-]+\.py\b", r"\b[\w-]+\.json\b"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, body))


if __name__ == "__main__":
    unittest.main()
