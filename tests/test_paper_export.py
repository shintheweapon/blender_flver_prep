# Tests for docs/paper/export_docx.py: the paper's Markdown is rewritten so that pandoc can turn every equation into a
# Word equation, keep every table caption and point every image at its exported file. No browser code is imported.

import os
import re
import sys
import unittest

PAPER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "paper")
if PAPER_DIR not in sys.path:
    sys.path.insert(0, PAPER_DIR)

import export_docx  # noqa: E402


class TestPrepareMarkdown(unittest.TestCase):
    """The rewrite for pandoc's Word output."""

    @classmethod
    def setUpClass(cls):
        with open(export_docx.PAPER, encoding="utf-8") as file:
            cls.paper = file.read()
        cls.prepared = export_docx.prepare_markdown(cls.paper)

    def test_no_tag_is_left_and_every_number_stays(self):
        numbers = export_docx.TAG.findall(self.paper)
        self.assertEqual(len(numbers), 21)
        self.assertNotIn("\\tag{", self.prepared)
        for number in numbers:
            with self.subTest(number=number):
                self.assertIn(f"\\qquad ({number})", self.prepared)

    def test_every_table_caption_becomes_a_pandoc_caption(self):
        captions = export_docx.TABLE_CAPTION.findall(self.paper)
        self.assertEqual(len(captions), 6)
        self.assertNotIn('<p align="center">TABLE', self.prepared)
        for numeral, caption in captions:
            with self.subTest(table=numeral):
                self.assertIn(f"Table: TABLE {numeral}. {caption}", self.prepared)

    def test_every_image_points_at_its_export(self):
        sources = export_docx.images(self.paper)
        self.assertEqual(len(sources), 12)
        exported = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", self.prepared)
        self.assertEqual(exported, [export_docx.export_name(s) for s in sources])
        gifs = [name for name in exported if name.endswith(".gif")]
        self.assertEqual(gifs, ["paper_axis_swap_animated.gif", "paper_dome_tilts.gif"])
        self.assertTrue(all(name.endswith(".png") for name in exported if name not in gifs))

    def test_widths_are_given_where_known(self):
        prepared = export_docx.prepare_markdown(self.paper, {"tangent_frame.png": 6.5})
        self.assertIn("(tangent_frame.png){width=6.50in}", prepared)

    def test_pandoc_reads_markdown_without_implicit_figures(self):
        command = export_docx.pandoc_command("out.docx")
        self.assertEqual(command[:3], ["pandoc", "-f", "markdown-implicit_figures"])
        self.assertEqual(command[-2:], ["-o", "out.docx"])

    def test_svg_size_is_read_from_the_svg(self):
        self.assertEqual(export_docx.svg_size('<svg xmlns="x" width="680" height="370" viewBox="0 0 680 370">'),
                         (680.0, 370.0))


class TestTableBorders(unittest.TestCase):
    """Every table gets a grid written into it, once."""

    SAMPLE = ('<w:body><w:p><w:t>before</w:t></w:p>'
              '<w:tbl><w:tblPr><w:tblStyle w:val="Table" /><w:tblW w:type="pct" w:w="5000" /></w:tblPr></w:tbl>'
              '<w:tbl><w:tblPr><w:tblStyle w:val="Table" /><w:tblLook w:val="0020" /></w:tblPr></w:tbl></w:body>')

    def test_each_table_gets_six_edges_right_after_its_style(self):
        result = export_docx.add_table_borders(self.SAMPLE)
        properties = re.findall(r"<w:tblPr>(.*?)</w:tblPr>", result)
        self.assertEqual(len(properties), 2)
        for block in properties:
            self.assertTrue(block.startswith('<w:tblStyle w:val="Table" /><w:tblBorders>'))
            for edge in export_docx.BORDER_EDGES:
                self.assertIn(f'<w:{edge} w:val="single" w:sz="4"', block)

    def test_running_twice_adds_nothing_more(self):
        once = export_docx.add_table_borders(self.SAMPLE)
        self.assertEqual(export_docx.add_table_borders(once), once)
        self.assertEqual(once.count("<w:tblBorders>"), 2)

    def test_text_outside_tables_is_unchanged(self):
        result = export_docx.add_table_borders(self.SAMPLE)
        self.assertTrue(result.startswith("<w:body><w:p><w:t>before</w:t></w:p>"))


if __name__ == "__main__":
    unittest.main()
