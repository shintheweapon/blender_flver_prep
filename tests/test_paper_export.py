# Tests for docs/paper/export_docx.py: the paper's Markdown is rewritten so that pandoc can turn every equation into a
# Word equation, keep every table caption and point every image at its exported file. No browser code is imported.

import os
import re
import sys
import tempfile
import unittest
import zipfile

PAPER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "paper")
if PAPER_DIR not in sys.path:
    sys.path.insert(0, PAPER_DIR)

import docx_xml  # noqa: E402
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


class TestChineseExport(unittest.TestCase):
    """The Chinese paper's Markdown is prepared the same way, with its own caption label."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(PAPER_DIR, "ER_NORMAL_MAPS.zh-CN.md"), encoding="utf-8") as file:
            cls.paper = file.read()
        cls.prepared = export_docx.prepare_markdown(cls.paper)

    def test_every_table_caption_becomes_a_pandoc_caption(self):
        captions = export_docx.TABLE_CAPTION.findall(self.paper)
        self.assertEqual(len(captions), 6)
        self.assertNotIn('<p align="center">表', self.prepared)
        for numeral, caption in captions:
            with self.subTest(table=numeral):
                self.assertIn(f"Table: 表 {numeral}　{caption}", self.prepared)

    def test_animated_chinese_figures_get_their_gif_timing(self):
        for name in ("paper_axis_swap_animated.zh.svg", "paper_dome_tilts.zh.svg"):
            with self.subTest(figure=name):
                self.assertEqual(export_docx.gif_timing("../figures/" + name),
                                 export_docx.GIF_TIMING[name.replace(".zh.svg", ".svg")])
                self.assertTrue(export_docx.export_name("../figures/" + name).endswith(".zh.gif"))

    def test_the_chinese_figures_lead_with_the_video_fonts(self):
        with open(os.path.join(os.path.dirname(PAPER_DIR), "figures", "paper_layout_test.zh.svg"),
                  encoding="utf-8") as file:
            svg = export_docx.scenes.with_video_fonts(file.read())
        self.assertIn(export_docx.scenes.chinese_figure_stack(), svg)
        self.assertTrue(export_docx.scenes.chinese_figure_stack().index("Source Han Sans SC")
                        < export_docx.scenes.chinese_figure_stack().index("Noto Sans SC"))


class TestLanguageLine(unittest.TestCase):
    """Both Word files start at the title: the line linking the other paper's Markdown file is left out."""

    def test_the_line_is_dropped_in_both_languages(self):
        for name in ("ER_NORMAL_MAPS.md", "ER_NORMAL_MAPS.zh-CN.md"):
            with open(os.path.join(PAPER_DIR, name), encoding="utf-8") as file:
                paper = file.read()
            prepared = export_docx.prepare_markdown(paper)
            with self.subTest(paper=name):
                self.assertNotRegex(prepared, export_docx.LANGUAGE_LINE)
                self.assertTrue(prepared.startswith(paper.split("\n")[0] + "\n\n"))
                self.assertEqual(prepared.split("\n")[2], paper.split("\n")[4])

    def test_nothing_else_changes(self):
        text = "# Title\n\nEnglish | [简体中文](ER_NORMAL_MAPS.zh-CN.md)\n\nBody, linking [x](ER_NORMAL_MAPS.md) later.\n" \
               + "\n" * 6 + "end"
        self.assertEqual(export_docx.drop_language_line(text),
                         "# Title\n\nBody, linking [x](ER_NORMAL_MAPS.md) later.\n" + "\n" * 6 + "end")
        self.assertEqual(export_docx.drop_language_line("# Title\n\nNo links.\n"), "# Title\n\nNo links.\n")


class TestWordPackage(unittest.TestCase):
    """The page number in the footer, the East Asian font, and the rewrite of the Word package."""

    STYLES = ('<w:styles><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:asciiTheme="minorHAnsi" '
              'w:cstheme="minorBidi" w:eastAsiaTheme="minorHAnsi" w:hAnsiTheme="minorHAnsi" /><w:sz w:val="24" />'
              '<w:lang w:bidi="ar-SA" w:eastAsia="en-US" w:val="en-US" /></w:rPr></w:rPrDefault></w:docDefaults>'
              '<w:style><w:rPr><w:rFonts w:asciiTheme="majorHAnsi" w:eastAsiaTheme="majorEastAsia" /></w:rPr></w:style>'
              '<w:style><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" /></w:rPr></w:style></w:styles>')

    def test_east_asian_text_gets_the_font_and_language(self):
        styles = docx_xml.set_east_asian_font(self.STYLES, "Noto Sans SC", "zh-CN")
        self.assertNotIn("eastAsiaTheme", styles)
        self.assertEqual(styles.count('w:eastAsia="Noto Sans SC"'), 3)
        self.assertIn('w:asciiTheme="minorHAnsi"', styles)
        self.assertIn('w:hAnsi="Consolas"', styles)
        self.assertIn('<w:lang w:bidi="ar-SA" w:eastAsia="zh-CN" w:val="zh-CN" />', styles)
        self.assertEqual(docx_xml.set_east_asian_font(styles, "Noto Sans SC", "zh-CN"), styles)

    def test_the_footer_holds_a_centred_page_field(self):
        footer = docx_xml.footer_xml()
        self.assertIn('<w:jc w:val="center"/>', footer)
        self.assertIn("> PAGE <", footer)
        for kind in ("begin", "separate", "end"):
            self.assertIn(f'w:fldCharType="{kind}"', footer)

    def test_the_last_section_refers_to_the_footer_once(self):
        reference = '<w:footerReference w:type="default" r:id="rIdPageNumbers"/>'
        for body, expected in (
                ("<w:body><w:p/><w:sectPr /></w:body>", f"<w:body><w:p/><w:sectPr>{reference}</w:sectPr></w:body>"),
                ("<w:body><w:p/></w:body>", f"<w:body><w:p/><w:sectPr>{reference}</w:sectPr></w:body>"),
                ('<w:body><w:sectPr w:rsidR="1"><w:pgSz/></w:sectPr></w:body>',
                 f'<w:body><w:sectPr w:rsidR="1">{reference}<w:pgSz/></w:sectPr></w:body>')):
            with self.subTest(body=body):
                once = docx_xml.add_footer(body)
                self.assertEqual(once, expected)
                self.assertEqual(docx_xml.add_footer(once), once)

    def test_relationship_and_content_type_are_added_once(self):
        rels = '<Relationships><Relationship Id="rId1" Target="styles.xml" /></Relationships>'
        once = docx_xml.add_relationship(rels, "rIdPageNumbers", docx_xml.FOOTER_TYPE, "footer1.xml")
        self.assertIn('Id="rId1"', once)
        self.assertEqual(once.count('Id="rIdPageNumbers"'), 1)
        self.assertEqual(docx_xml.add_relationship(once, "rIdPageNumbers", docx_xml.FOOTER_TYPE, "footer1.xml"), once)
        types = '<Types><Override PartName="/word/document.xml" ContentType="x" /></Types>'
        once = docx_xml.add_override(types, "word/footer1.xml", docx_xml.FOOTER_CONTENT)
        self.assertIn('PartName="/word/footer1.xml"', once)
        self.assertIn('PartName="/word/document.xml"', once)
        self.assertEqual(docx_xml.add_override(once, "word/footer1.xml", docx_xml.FOOTER_CONTENT), once)

    def test_rewrite_package_changes_adds_and_keeps_the_rest(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "sample.docx")
            with zipfile.ZipFile(path, "w") as package:
                package.writestr("word/document.xml", "<doc/>")
                package.writestr("word/media/a.png", b"\x89PNG kept")
            docx_xml.rewrite_package(path, {"word/document.xml": lambda xml: xml.replace("doc", "changed")},
                                     {"word/footer1.xml": b"<ftr/>"})
            with zipfile.ZipFile(path) as package:
                self.assertEqual(package.namelist(), ["word/document.xml", "word/media/a.png", "word/footer1.xml"])
                self.assertEqual(package.read("word/document.xml"), b"<changed/>")
                self.assertEqual(package.read("word/media/a.png"), b"\x89PNG kept")
                self.assertEqual(package.read("word/footer1.xml"), b"<ftr/>")


class TestUpright(unittest.TestCase):
    """Numbers in maths and table captions are upright; variables stay italic."""

    def test_numbers_in_maths_become_upright(self):
        xml = ('<m:oMath><m:r><m:t>W</m:t></m:r><m:r><m:rPr><m:sty m:val="p" /></m:rPr><m:t>=</m:t></m:r>'
               '<m:r><m:t>0.125</m:t></m:r><m:r><m:rPr><m:sty m:val="p" /></m:rPr><m:t>(</m:t></m:r>'
               '<m:r><m:t>10</m:t></m:r><m:r><m:rPr><m:nor /></m:rPr><m:t>2</m:t></m:r></m:oMath>')
        out = docx_xml.upright_numbers(xml)
        self.assertIn('<m:r><m:rPr><m:sty m:val="p" /></m:rPr><m:t>0.125</m:t></m:r>', out)
        self.assertIn('<m:r><m:rPr><m:sty m:val="p" /></m:rPr><m:t>10</m:t></m:r>', out)
        self.assertIn("<m:r><m:t>W</m:t></m:r>", out)
        self.assertIn("<m:rPr><m:nor /></m:rPr><m:t>2</m:t>", out)
        self.assertEqual(docx_xml.upright_numbers(out), out)

    def test_table_captions_are_upright_and_small_caps_when_asked(self):
        styles = ('<w:styles><w:style w:styleId="Caption"><w:rPr><w:i /></w:rPr></w:style>'
                  '<w:style w:customStyle="1" w:styleId="TableCaption" w:type="paragraph"><w:name w:val="Table Caption" />'
                  '<w:basedOn w:val="Caption" /><w:pPr><w:keepNext /></w:pPr></w:style></w:styles>')
        english = docx_xml.set_caption_style(styles, small_caps=True)
        self.assertIn('<w:pPr><w:keepNext /></w:pPr><w:rPr><w:i w:val="0" /><w:smallCaps /></w:rPr></w:style>', english)
        self.assertIn('w:styleId="Caption"><w:rPr><w:i /></w:rPr>', english)
        chinese = docx_xml.set_caption_style(styles, small_caps=False)
        self.assertIn('<w:rPr><w:i w:val="0" /></w:rPr></w:style>', chinese)
        self.assertNotIn("smallCaps", chinese)
        self.assertEqual(docx_xml.set_caption_style(english, small_caps=True), english)


if __name__ == "__main__":
    unittest.main()
