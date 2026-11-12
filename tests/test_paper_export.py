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


CELL = '<w:tc><w:p><w:pPr><w:pStyle w:val="Compact" /></w:pPr><w:r><w:t>{}</w:t></w:r></w:p></w:tc>'


class TestFormatTables(unittest.TestCase):
    """Every table gets its grid, centring, rows that stay together and a bold header, once."""

    SAMPLE = ('<w:body><w:p><w:t>before</w:t></w:p>'
              '<w:p><w:pPr><w:pStyle w:val="TableCaption" /></w:pPr><w:r><w:t>TABLE I. X</w:t></w:r></w:p>'
              '<w:tbl><w:tblPr><w:tblStyle w:val="Table" /><w:tblW w:type="pct" w:w="5000" />'
              '<w:tblLook w:firstRow="1" w:val="0020" /><w:tblCaption w:val="TABLE I. X" /></w:tblPr>'
              '<w:tblGrid><w:gridCol w:w="100" /></w:tblGrid>'
              + "".join("<w:tr>" + CELL.format(t) + CELL.format(t) + "</w:tr>" for t in ("Head", "a", "b"))
              + '</w:tbl></w:body>')

    @classmethod
    def setUpClass(cls):
        cls.result = export_docx.format_tables(cls.SAMPLE)
        cls.rows = re.findall(r"<w:tr>(.*?)</w:tr>", cls.result)

    def test_table_properties_are_in_schema_order(self):
        block = re.search(r"<w:tblPr>(.*?)</w:tblPr>", self.result).group(1)
        names = [name for name, _ in export_docx.child_elements(block)]
        self.assertEqual(names, ["tblStyle", "tblW", "jc", "tblBorders", "tblLook", "tblCaption"])
        self.assertIn('<w:tblW w:type="auto" w:w="0"/>', block)
        self.assertIn('<w:jc w:val="center"/>', block)
        self.assertIn('w:firstRow="0"', block)
        for edge in export_docx.BORDER_EDGES:
            self.assertIn(f'<w:{edge} w:val="single" w:sz="4"', block)

    def test_every_cell_has_its_own_four_borders_first(self):
        cells = re.findall(r"<w:tc>(.*?)</w:tc>", self.result)
        self.assertEqual(len(cells), 6)
        for cell in cells:
            self.assertTrue(cell.startswith("<w:tcPr><w:tcBorders>"))
            for edge in export_docx.BORDER_EDGES[:4]:
                self.assertIn(f"<w:{edge} ", cell)

    def test_rows_stay_together(self):
        self.assertTrue(all(row.startswith("<w:trPr><w:cantSplit/></w:trPr>") for row in self.rows))
        self.assertTrue(all("<w:keepNext/>" in row for row in self.rows[:-1]))
        self.assertNotIn("<w:keepNext/>", self.rows[-1])

    def test_the_header_is_bold_and_the_caption_centred(self):
        self.assertEqual(self.rows[0].count("<w:rPr><w:b/></w:rPr>"), 2)
        self.assertNotIn("<w:b/>", self.rows[1])
        self.assertIn('<w:pStyle w:val="TableCaption" /><w:jc w:val="center"/>', self.result)

    def test_running_twice_changes_nothing(self):
        self.assertEqual(export_docx.format_tables(self.result), self.result)

    def test_text_outside_tables_is_unchanged(self):
        self.assertTrue(self.result.startswith("<w:body><w:p><w:t>before</w:t></w:p>"))


if __name__ == "__main__":
    unittest.main()
