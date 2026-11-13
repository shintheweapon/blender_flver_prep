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

import docx_styles  # noqa: E402
import docx_tables  # noqa: E402
import docx_xml  # noqa: E402
import export_docx  # noqa: E402
import math_images  # noqa: E402


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
        styles = docx_styles.set_east_asian_font(self.STYLES, "Noto Sans SC", "zh-CN")
        self.assertNotIn("eastAsiaTheme", styles)
        self.assertEqual(styles.count('w:eastAsia="Noto Sans SC"'), 3)
        self.assertIn('w:asciiTheme="minorHAnsi"', styles)
        self.assertIn('w:hAnsi="Consolas"', styles)
        self.assertIn('<w:lang w:bidi="ar-SA" w:eastAsia="zh-CN" w:val="zh-CN" />', styles)
        self.assertEqual(docx_styles.set_east_asian_font(styles, "Noto Sans SC", "zh-CN"), styles)

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
        english = docx_styles.set_caption_style(styles, small_caps=True)
        self.assertIn('<w:pPr><w:keepNext /></w:pPr><w:rPr><w:i w:val="0" /><w:smallCaps /></w:rPr></w:style>', english)
        self.assertIn('w:styleId="Caption"><w:rPr><w:i /></w:rPr>', english)
        chinese = docx_styles.set_caption_style(styles, small_caps=False)
        self.assertIn('<w:rPr><w:i w:val="0" /></w:rPr></w:style>', chinese)
        self.assertNotIn("smallCaps", chinese)
        self.assertEqual(docx_styles.set_caption_style(english, small_caps=True), english)


class TestColumnWidths(unittest.TestCase):
    """Columns are sized to their content, so no word breaks inside a cell."""

    def test_the_widest_word_sets_a_columns_minimum(self):
        rows = [[["Prefix"], ["Untestable"]], [["WP"], ["2"]]]
        minimums, preferred = docx_tables.column_bounds(rows)
        factor = docx_tables.TEXT_SLACK * docx_tables.HEADER_FACTOR
        self.assertEqual(minimums[1], int(round(len("Untestable") * 120 * factor)) + docx_tables.CELL_PADDING)
        self.assertEqual(preferred, minimums)

    def test_quotes_count_with_their_word_and_chinese_keeps_four_characters(self):
        minimums, _ = docx_tables.column_bounds([[["名称"]], [["材质名称包含“cloth”"]]])
        widest = max(len("“cloth”") * 120, 4 * 240)
        self.assertEqual(minimums[0], int(round(widest * docx_tables.TEXT_SLACK)) + docx_tables.CELL_PADDING)

    def test_lines_split_at_a_break_are_measured_apart(self):
        one = docx_tables.column_bounds([[["前缀"]], [["WP（武器）"]]])[1][0]
        two = docx_tables.column_bounds([[["前缀"]], [["WP", "（武器）"]]])[1][0]
        self.assertLess(two, one)

    def test_widths_fit_and_preferred_widths_are_kept_when_they_fit(self):
        rows = [[["a"], ["b"]], [["x " * 30], ["short"]]]
        widths, squeezed = docx_tables.column_widths(rows, 5000)
        self.assertLessEqual(sum(widths), 5000)
        self.assertFalse(squeezed)
        _, preferred = docx_tables.column_bounds(rows)
        self.assertEqual(docx_tables.column_widths(rows, 100000), (preferred, False))

    def test_minimums_that_do_not_fit_are_reported(self):
        widths, squeezed = docx_tables.column_widths([[["Untestable"], ["Untestable"]]], 1000)
        self.assertTrue(squeezed)
        self.assertLessEqual(sum(widths), 1000)


class TestTableLayout(unittest.TestCase):
    """The computed widths are written into every table, and a first-column bracket starts its own line."""

    TABLE = ('<w:tbl><w:tblPr><w:tblW w:type="auto" w:w="0"/><w:jc w:val="center"/></w:tblPr>'
             '<w:tr><w:tc><w:tcPr><w:tcBorders/></w:tcPr><w:p><w:r><w:t>前缀</w:t></w:r></w:p></w:tc>'
             '<w:tc><w:p><w:r><w:t>可检验贴图</w:t></w:r></w:p></w:tc></w:tr>'
             '<w:tr><w:tc><w:p><w:r><w:t xml:space="preserve">WP（武器）</w:t></w:r></w:p></w:tc>'
             '<w:tc><w:p><w:r><w:t>535（不是名称）</w:t></w:r></w:p></w:tc></w:tr></w:tbl>')

    def test_grid_cell_widths_and_fixed_layout(self):
        out = docx_tables.set_table_widths(self.TABLE, 10080)
        grid = re.findall(r'<w:gridCol w:w="(\d+)"/>', out)
        self.assertEqual(len(grid), 2)
        self.assertEqual(len(re.findall(r'<w:tcW w:type="dxa" w:w="\d+"/>', out)), 4)
        self.assertIn(f'<w:tblW w:type="dxa" w:w="{sum(map(int, grid))}"/><w:jc w:val="center"/>', out)
        self.assertIn('<w:tblLayout w:type="fixed"/>' + docx_tables.CELL_MARGINS + '</w:tblPr><w:tblGrid>', out)
        self.assertIn("<w:tcPr><w:tcW", out)
        self.assertEqual(docx_tables.set_table_widths(out, 10080), out)

    def test_a_first_column_bracket_starts_its_own_line(self):
        out = docx_tables.break_before_brackets(self.TABLE)
        self.assertIn('WP</w:t><w:br/><w:t xml:space="preserve">（武器）', out)
        self.assertEqual(out.count("<w:br/>"), 1)
        self.assertIn("535（不是名称）", out)
        self.assertEqual(docx_tables.break_before_brackets(out), out)


class TestPageAndFigures(unittest.TestCase):
    """US Letter pages with 0.75 in margins, figures kept with their captions, and a height cap."""

    def test_page_size_and_margins_after_the_footer(self):
        body = '<w:body><w:p/><w:sectPr><w:footerReference w:type="default" r:id="x"/></w:sectPr></w:body>'
        out = docx_xml.set_page(body, 1080)
        self.assertIn('r:id="x"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080"', out)
        self.assertEqual(docx_xml.set_page(out, 1080), out)
        self.assertIn("<w:sectPr><w:pgSz", docx_xml.set_page("<w:body><w:sectPr /></w:body>", 1080))

    def test_pictures_are_kept_with_the_next_paragraph(self):
        xml = ('<w:p><w:pPr><w:pStyle w:val="Figure" /></w:pPr><w:r><w:drawing>a</w:drawing></w:r></w:p>'
               '<w:p><w:r><w:drawing>b</w:drawing></w:r></w:p><w:p><w:r><w:t>Fig. 1.</w:t></w:r></w:p>')
        out = docx_xml.keep_figures_with_captions(xml)
        self.assertIn('<w:pStyle w:val="Figure" /><w:keepNext/>', out)
        self.assertIn("<w:p><w:pPr><w:keepNext/></w:pPr><w:r><w:drawing>b", out)
        self.assertNotIn("<w:keepNext/></w:pPr><w:r><w:t>Fig.", out)
        self.assertEqual(docx_xml.keep_figures_with_captions(out), out)

    def test_pictures_are_centred(self):
        xml = ('<w:p><w:pPr><w:pStyle w:val="BodyText" /><w:keepNext/></w:pPr><w:r><w:drawing>a</w:drawing></w:r></w:p>'
               '<w:p><w:r><w:drawing>b</w:drawing></w:r></w:p>'
               '<w:p><w:pPr><w:pStyle w:val="X" /><w:rPr><w:b/></w:rPr></w:pPr><w:r><w:drawing>c</w:drawing></w:r></w:p>'
               '<w:p><w:r><w:t>Fig. 1.</w:t></w:r></w:p>')
        out = docx_xml.centre_figures(xml)
        self.assertIn('<w:keepNext/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>a', out)
        self.assertIn('<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:drawing>b', out)
        self.assertIn('<w:pStyle w:val="X" /><w:jc w:val="center"/><w:rPr><w:b/></w:rPr></w:pPr>', out)
        self.assertIn("<w:p><w:r><w:t>Fig. 1.", out)
        self.assertEqual(docx_xml.centre_figures(out), out)

    def test_figures_are_no_taller_than_the_cap(self):
        self.assertAlmostEqual(export_docx.figure_width(680, 1065), 7.0 * 680 / 1065)
        self.assertAlmostEqual(export_docx.figure_width(1360, 636), 6.5)
        self.assertAlmostEqual(export_docx.figure_width(480, 200), 5.0)


class TestMathImages(unittest.TestCase):
    """Maths as pictures: the tree rewrite, the placement in the Word file and the table widths."""

    @staticmethod
    def math(kind, tex):
        return {"t": "Math", "c": [{"t": kind}, tex]}

    def tree(self):
        para = {"t": "Para", "c": [{"t": "Str", "c": "x"}, {"t": "Space"}, self.math("InlineMath", " a+b ")]}
        display = {"t": "Para", "c": [{"t": "SoftBreak"}, self.math("DisplayMath", "\n\\vec{n} = 1 \\qquad (3)\n")]}
        cell = {"t": "Plain", "c": [self.math("InlineMath", "W")]}
        return {"pandoc-api-version": [1, 22], "meta": {}, "blocks": [para, display, {"t": "Table", "c": [[cell]]}]}

    def test_split_number(self):
        self.assertEqual(math_images.split_number("\n\\vec{n} = 1 \\qquad (12)\n"), ("\\vec{n} = 1", "12"))
        self.assertEqual(math_images.split_number("a \\qquad b"), ("a \\qquad b", None))

    def test_math_nodes_in_order_and_names_by_kind(self):
        nodes = math_images.math_nodes(self.tree())
        self.assertEqual([kind for kind, _ in nodes], ["inline", "display", "inline"])
        self.assertEqual(math_images.image_name("inline", "a+b"), math_images.image_name("inline", " a+b "))
        self.assertRegex(math_images.image_name("display", "a+b"), r"^math_d_[0-9a-f]{12}\.png$")
        self.assertNotEqual(math_images.image_name("display", "a+b"), math_images.image_name("inline", "a+b"))
        self.assertEqual(len(math_images.distinct_items(self.tree())), 3)

    def test_replace_math_gives_pictures_and_numbers(self):
        tree = self.tree()
        sizes = {name: (1.0, 0.25, 1.5, False) for name, _, _ in math_images.distinct_items(tree)}
        out, numbers = math_images.replace_math(tree, sizes)
        self.assertEqual(numbers, ["3"])
        self.assertEqual(math_images.math_nodes(out), [])
        display = out["blocks"][1]["c"]
        self.assertEqual(len(display), 1)
        self.assertEqual(display[0]["c"][1], [{"t": "Str", "c": "\\vec{n} = 1"}])
        self.assertEqual(display[0]["c"][0][2], [["width", "1.000in"], ["height", "0.250in"]])
        self.assertTrue(display[0]["c"][2][0].startswith("math/math_d_"))
        self.assertEqual(math_images.math_nodes(tree)[0], ("inline", " a+b "))

    def test_picture_sizes(self):
        self.assertEqual(math_images.picture_size("inline", 96, 48, 8, 7.0), (1.0, 0.5, 6.0, False))
        width, height, depth, scaled = math_images.picture_size("display", 960, 96, 0, 7.0)
        self.assertTrue(scaled)
        self.assertAlmostEqual(width, 7.0 - math_images.NUMBER_ROOM_INCHES)
        self.assertAlmostEqual(height, width / 10)

    def test_place_math(self):
        inline = "math_i_" + "a" * 12 + ".png"
        display = "math_d_" + "b" * 12 + ".png"
        drawing = '<w:drawing><wp:extent cx="635000" cy="1"/><pic:cNvPr descr="math/{}" id="0"/></w:drawing>'
        xml = ('<w:p><w:pPr><w:pStyle w:val="BodyText" /></w:pPr><w:r><w:t>x</w:t></w:r><w:r>'
               + drawing.format(inline) + '</w:r></w:p>'
               '<w:p><w:pPr><w:pStyle w:val="BodyText" /><w:jc w:val="center"/></w:pPr><w:r>'
               + drawing.format(display) + '</w:r></w:p>'
               '<w:p><w:r><w:drawing><pic:cNvPr descr="figure.png"/></w:drawing></w:r></w:p>')
        sizes = {inline: (1.0, 0.2, 2.5, False), display: (3.0, 0.5, 0.0, False)}
        out = math_images.place_math(xml, sizes, ["7"], 10080)
        self.assertIn('<w:r><w:rPr><w:position w:val="-5"/></w:rPr><w:drawing>', out)
        self.assertIn('<w:pStyle w:val="BodyText" /><w:tabs><w:tab w:val="center" w:pos="5040"/>'
                      '<w:tab w:val="right" w:pos="10080"/></w:tabs></w:pPr><w:r><w:tab/></w:r><w:r><w:drawing>', out)
        self.assertIn("</w:drawing></w:r><w:r><w:tab/><w:t>(7)</w:t></w:r></w:p>", out)
        self.assertNotIn("<w:jc", out)
        self.assertIn('<w:p><w:r><w:drawing><pic:cNvPr descr="figure.png"/>', out)
        self.assertEqual(math_images.place_math(out, sizes, ["7"], 10080), out)

    def test_figure_edits_skip_maths_pictures(self):
        maths = '<w:p><w:r><w:drawing><pic:cNvPr descr="math_i_' + "c" * 12 + '.png"/></w:drawing></w:r></w:p>'
        self.assertFalse(docx_xml.holds_figure(maths))
        self.assertEqual(docx_xml.centre_figures(docx_xml.keep_figures_with_captions(maths)), maths)
        self.assertTrue(docx_xml.holds_figure('<w:p><w:r><w:drawing>a</w:drawing></w:r></w:p>'))

    def test_a_picture_in_a_cell_is_measured(self):
        cell = ('<w:tc><w:p><w:r><w:t>by</w:t></w:r><w:r><w:drawing><wp:extent cx="762000" cy="1"/>'
                '</w:drawing></w:r></w:p></w:tc>')
        self.assertEqual(docx_tables.cell_lines(cell), ["by" + "x" * 10])

    def test_the_page_escapes_tex_and_marks_display(self):
        page = math_images.math_page([("n", "display", 'a<b "c"'), ("m", "inline", "x")], "<head-tags>")
        self.assertIn('data-tex="a&lt;b &quot;c&quot;" data-display="1"', page)
        self.assertIn('data-tex="x" data-display="0"', page)
        self.assertIn("<head-tags>", page)
        self.assertIn("Source Han Sans SC", page)


if __name__ == "__main__":
    unittest.main()
