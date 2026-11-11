# Tests for docs/paper/ER_NORMAL_MAPS.md: its equations, citations and figures are complete and in order, and its
# worked example is what the functions in docs/figures/tangent_geometry.py compute

import os
import re
import sys
import unittest

DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
PAPER_DIR = os.path.join(DOCS_DIR, "paper")
PAPER = os.path.join(PAPER_DIR, "ER_NORMAL_MAPS.md")
FIGURES_DIR = os.path.join(DOCS_DIR, "figures")
if FIGURES_DIR not in sys.path:
    sys.path.insert(0, FIGURES_DIR)

import frame_survey  # noqa: E402
import layout_results  # noqa: E402
import tangent_geometry as mf  # noqa: E402
from paper_figures import prefix_label  # noqa: E402

REFERENCES_HEADING = "## References"


def read_paper():
    with open(PAPER, encoding="utf-8") as file:
        return file.read()


def display_equations(text):
    """
    The displayed equations, each with the first non-empty line after it.

    Returns
    -------
    list of tuple
        ``(body, following_line)`` per ``$$`` block.
    """
    lines = text.splitlines()
    blocks, i = [], 0
    while i < len(lines):
        if lines[i].strip() == "$$":
            end = next(j for j in range(i + 1, len(lines)) if lines[j].strip() == "$$")
            following = next((line for line in lines[end + 1:] if line.strip()), "")
            blocks.append(("\n".join(lines[i + 1:end]), following))
            i = end + 1
        else:
            i += 1
    return blocks


def without_maths(text):
    """The text with displayed and inline maths removed."""
    text = re.sub(r"^\$\$$.*?^\$\$$", "", text, flags=re.MULTILINE | re.DOTALL)
    return re.sub(r"\$[^$\n]+\$", "", text)


def number(value):
    """A number as the paper writes it: whole numbers without a decimal point."""
    value = 0.0 if abs(value) < 1e-12 else value
    return str(int(round(value))) if abs(value - round(value)) < 1e-12 else repr(round(value, 6))


def vector(values):
    return "(" + ", ".join(number(v) for v in values) + ")"


class TestEquations(unittest.TestCase):

    def test_every_displayed_equation_is_followed_by_in_words(self):
        for body, following in display_equations(read_paper()):
            with self.subTest(equation=body[:60]):
                self.assertTrue(following.startswith("*In words:*"), following)

    def test_equations_are_numbered_one_by_one(self):
        tags = []
        for body, _ in display_equations(read_paper()):
            found = re.findall(r"\\tag\{(\d+)\}", body)
            self.assertEqual(len(found), 1, body[:60])
            tags.append(int(found[0]))
        self.assertEqual(tags, list(range(1, len(tags) + 1)))

    def test_equation_references_point_at_existing_equations(self):
        text = read_paper()
        count = len(display_equations(text))
        body = text.split(REFERENCES_HEADING)[0]
        for cited in re.findall(r"(?<![\w$])\((\d+)\)", without_maths(body)):
            self.assertLessEqual(int(cited), count)


class TestCitations(unittest.TestCase):

    def test_every_citation_has_a_reference_and_every_reference_is_cited(self):
        text = read_paper()
        body, references = text.split(REFERENCES_HEADING)
        cited = {int(n) for n in re.findall(r"\[(\d+)\](?!\()", body)}
        listed = [int(n) for n in re.findall(r"^\[(\d+)\] ", references, flags=re.MULTILINE)]
        self.assertEqual(listed, list(range(1, len(listed) + 1)))
        self.assertEqual(cited, set(listed))

    def test_references_are_numbered_in_order_of_first_citation(self):
        body = read_paper().split(REFERENCES_HEADING)[0]
        first = []
        for n in re.findall(r"\[(\d+)\](?!\()", body):
            if int(n) not in first:
                first.append(int(n))
        self.assertEqual(first, list(range(1, len(first) + 1)))

    def test_every_online_reference_has_an_access_date(self):
        references = read_paper().split(REFERENCES_HEADING)[1]
        for entry in re.split(r"\n\n+", references.strip()):
            if "[Online]" in entry:
                with self.subTest(entry=entry[:40]):
                    self.assertRegex(entry, r"Accessed: [A-Z][a-z]{2}\.? \d{1,2}, \d{4}\.")


class TestFigures(unittest.TestCase):

    def test_every_image_exists(self):
        for path in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", read_paper()):
            with self.subTest(path=path):
                self.assertTrue(os.path.isfile(os.path.normpath(os.path.join(PAPER_DIR, path))))

    def test_figures_are_numbered_one_by_one(self):
        numbers = [int(n) for n in re.findall(r"^\*Fig\. (\d+)\.", read_paper(), flags=re.MULTILINE)]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))

    def test_screenshots(self):
        # The two in-game screenshots, cropped and small, each with alt text
        shots = re.findall(r"!\[([^\]]*)\]\((images/[^)]+)\)", read_paper())
        self.assertEqual([path for _, path in shots], ["images/ingame_layout_test.webp", "images/ingame_er_tangents.webp"])
        for alt, path in shots:
            with self.subTest(path=path):
                self.assertTrue(alt.startswith("In game:"))
                self.assertLess(os.path.getsize(os.path.join(PAPER_DIR, path)), 300 * 1024)


class TestWorkedExample(unittest.TestCase):
    """The numbers in the paper's worked example are what tangent_geometry computes."""

    POSITIONS = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 0.0, 1.0)]
    UVS = [(0.0, 0.0), (0.5, 0.0), (0.0, 0.25)]
    NORMAL = (0.0, -1.0, 0.0)

    def example_text(self):
        text = read_paper()
        return text[text.index("**Worked example.**"):text.index("**Validation.**")]

    def test_inputs_are_the_ones_tested(self):
        text = self.example_text()
        for i, p in enumerate(self.POSITIONS):
            self.assertIn(f"$\\vec{{p}}_{i} = {vector(p)}$", text)
        for uv in self.UVS:
            self.assertIn(f"${vector(uv)}$", text)
        self.assertIn(f"$\\vec{{N}} = {vector(self.NORMAL)}$", text)

    def test_values_are_the_computed_ones(self):
        d, dp_du, dp_dv = mf.uv_derivatives(self.POSITIONS, self.UVS)
        [(t, w)] = mf.build_frame(self.POSITIONS, [self.NORMAL] * 3, self.UVS, [(0, 1, 2)],
                                  [(0.0, 0.0, 0.0, 1.0)] * 3)[:1]
        n_x_t = mf.cross(self.NORMAL, t)
        rows = {
            "$d$ by (15)": f"${number(d)}$",
            "$\\partial\\vec{p}/\\partial u$ by (16)": f"${vector(dp_du)}$",
            "$\\partial\\vec{p}/\\partial v$ by (16)": f"${vector(dp_dv)}$",
            "$\\vec{T}$ by (18)": f"${vector(t)}$",
            "$\\vec{N}\\times\\vec{T}$ by (2)": f"${vector(n_x_t)}$",
            "$W$ by (19), and by (9)": f"${number(w)}$",
            "$\\vec{B}$ by (6)": f"${vector(tuple(w * c for c in n_x_t))}$",
        }
        table = {}
        for line in self.example_text().splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) == 2:
                table[cells[0]] = cells[1]
        for quantity, value in rows.items():
            with self.subTest(quantity=quantity):
                self.assertIn(quantity, table)
                self.assertTrue(table[quantity].startswith(value), table[quantity])


class TestTestSections(unittest.TestCase):
    """Every test the paper reports opens with its question and ends with its impact on the implementation."""

    LEAD_INS = ("**Question.**", "**Why it matters.**", "**How the test answers it.**", "**Result.**",
                "**Impact on the implementation.**")
    SECTIONS = (("### C. The Handedness of FLVER Space", "## IV. Measurements"),
                ("### A. The Integrability Test", "### B. Vanilla Frames"),
                ("### B. Vanilla Frames", "### C. The In-Game Test"),
                ("### C. The In-Game Test", "### D. Import Measurements"),
                ("### D. Import Measurements", "## V. "),
                ("**Validation.**", "**Relation to MikkTSpace.**"))

    def test_each_test_has_the_lead_ins_in_order(self):
        text = read_paper()
        for start, end in self.SECTIONS:
            section = text[text.index(start):text.index(end, text.index(start))]
            with self.subTest(section=start):
                starts = [line for line in section.splitlines() if line.startswith("**") and ".**" in line]
                found = [lead for line in starts for lead in self.LEAD_INS if line.startswith(lead)]
                self.assertEqual(found, list(self.LEAD_INS))


class TestLayoutTable(unittest.TestCase):
    """Section IV-A's table and counts are the committed results of the layout test."""

    def section(self):
        text = read_paper()
        return text[text.index("### A. The Integrability Test"):text.index("### B. Vanilla Frames")]

    def test_table_rows_are_the_summary(self):
        rows = layout_results.summary(layout_results.load()["maps"])
        lines = [line for line in self.section().splitlines() if line.startswith("| ") and "---" not in line][1:]
        self.assertEqual(len(lines), len(rows))
        for line, row in zip(lines, rows):
            with self.subTest(prefix=row["prefix"]):
                cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                self.assertEqual(cells, [prefix_label(row["prefix"]), str(row["tested"]), str(row["untestable"]),
                                         f"{100 * row['count']['directx+'] / row['tested']:.1f}%",
                                         f"{row['directx_median']:.2f}", f"{row['swapped_median']:.2f}"])

    def test_totals_are_the_summary(self):
        maps = layout_results.load()["maps"]
        testable = [m for m in maps if m["outcome"] != layout_results.UNTESTABLE]
        wins = sum(m["outcome"] == "directx+" for m in testable)
        text = self.section()
        for value in (len(maps), len(maps) - len(testable), len(testable), wins, len(testable) - wins):
            with self.subTest(value=value):
                self.assertRegex(text, rf"\b{value:,}\b")


class TestFrameTable(unittest.TestCase):
    """Section IV-B's tables are the committed survey of every part model."""

    def section(self):
        text = read_paper()
        return text[text.index("### B. Vanilla Frames"):text.index("### C. The In-Game Test")]

    @staticmethod
    def pct(held):
        return f"{100 * held[0] / held[1]:.2f}%"

    def table(self, header):
        lines = self.section().splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith(header))
        rows = []
        for line in lines[start + 2:]:
            if not line.startswith("|"):
                break
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        return rows

    def test_prefix_table_is_the_survey(self):
        rows = frame_survey.summary_by_prefix(frame_survey.load())
        expected = [[prefix_label(r["prefix"]), str(r["parts"]), f"{r['corners']:,}",
                     f"{r['length'][0]:.3f} to {r['length'][1]:.3f}", f"{r['normal_dot_99']:.3f}",
                     f"{r['v_cos_median']:.3f}", self.pct(r["held"]["+"]), self.pct(r["held"]["-"])] for r in rows]
        self.assertEqual(self.table("| Prefix | Parts |"), expected)

    def test_cloth_table_is_the_survey(self):
        split = frame_survey.by_cloth(frame_survey.load())
        got = self.table("| Meshes | Meshes checked |")
        self.assertEqual([row[1:] for row in got],
                         [[f"{split[k]['meshes']:,}", f"{split[k]['parts']:,}", self.pct(split[k]["held"]["+"]),
                           self.pct(split[k]["held"]["-"])] for k in ("cloth", "other")])

    def test_material_file_table_is_the_survey(self):
        parts = frame_survey.load()
        counts = frame_survey.cloth_rule(parts)["counts"]
        corners = {}
        for part in parts:
            for mesh in part["meshes"]:
                behaviour = frame_survey.mesh_behaviour(mesh)
                if behaviour:
                    key = (frame_survey.is_cloth(mesh["mtd"]), behaviour)
                    corners[key] = corners.get(key, 0) + mesh["held"]["+"][1]
        got = self.table("| Material file | Meshes |")
        for row, cloth in zip(got, (True, False)):
            keeps, follows, mixed = (counts.get((cloth, b), 0) for b in
                                     (frame_survey.KEEPS, frame_survey.FOLLOWS, frame_survey.MIXED))
            agree = frame_survey.KEEPS if cloth else frame_survey.FOLLOWS
            total_corners = sum(v for (k, _), v in corners.items() if k == cloth)
            with self.subTest(cloth=cloth):
                self.assertEqual(row[1:], [f"{keeps + follows + mixed:,}", f"{keeps:,}", f"{follows:,}", f"{mixed:,}",
                                           f"{100 * counts.get((cloth, agree), 0) / (keeps + follows + mixed):.1f}%",
                                           f"{100 * corners.get((cloth, agree), 0) / total_corners:.1f}%"])

    def test_misfit_numbers_are_the_survey(self):
        parts = frame_survey.load()
        rule, found = frame_survey.cloth_rule(parts), frame_survey.misfits(parts)
        text = " ".join(self.section().split())
        [(part, _, corners)] = found["large_cloth_following"]
        for phrase in (f"on {rule['name_and_file_differ']} meshes; on {rule['file_right']} of them",
                       f"The {found['meshes']} meshes that do not agree hold {found['corners']:,} of the",
                       f"{found['small']} of them have fewer than {frame_survey.SMALL_MESH}",
                       f"The {found['large_other_mixed']['meshes']} mixed meshes",
                       f"at least {100 * found['large_other_mixed']['lowest_share']:.0f}% of them",
                       f"on {part}, follows (9) on all {corners:,}"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_part_count_is_the_survey(self):
        self.assertIn(f"{len(frame_survey.load()):,} parts with triangles", self.section())


ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")
CAPTION = re.compile(r'^<p align="center">TABLE ([IVX]+)<br>([^<]+)</p>$')


class TestTables(unittest.TestCase):
    """Tables are captioned and cited in the IEEE style: TABLE and a Roman numeral above each, cited in order."""

    def tables(self):
        """Per table, in order: the last non-empty line before its header row."""
        lines = read_paper().split(REFERENCES_HEADING)[0].splitlines()
        found = []
        for i, line in enumerate(lines):
            if line.startswith("|") and (i == 0 or not lines[i - 1].startswith("|")):
                before = next(lines[j] for j in range(i - 1, -1, -1) if lines[j].strip())
                found.append(before)
        return found

    def test_every_table_has_a_caption_numbered_in_order(self):
        captions = self.tables()
        self.assertTrue(captions)
        for number, line in zip(ROMAN, captions):
            with self.subTest(table=number):
                match = CAPTION.match(line)
                self.assertIsNotNone(match, line)
                self.assertEqual(match.group(1), number)
                text = match.group(2)
                self.assertEqual(text, text.upper())
                self.assertFalse(text.endswith("."))

    def test_tables_are_cited_in_order(self):
        body = read_paper().split(REFERENCES_HEADING)[0]
        text = "\n".join(line for line in body.splitlines() if not CAPTION.match(line))
        first = []
        for number in re.findall(r"\bTable ([IVX]+)\b", text):
            if number not in first:
                first.append(number)
        self.assertEqual(first, list(ROMAN[:len(self.tables())]))


class TestWording(unittest.TestCase):

    def test_no_dash_punctuation(self):
        text = without_maths(read_paper())
        self.assertNotIn("\u2014", text)
        self.assertNotIn("\u2013", text)
        self.assertNotRegex(text, r"(?<![-|])--(?![-|])")
        self.assertNotRegex(text, r"[A-Za-z,] - [A-Za-z]")

    def test_equation_numbers_do_not_start_a_sentence(self):
        # IEEE: "Equation (1)" at the start of a sentence, "(1)" elsewhere, never "Eq. (1)"
        body = without_maths(read_paper().split(REFERENCES_HEADING)[0])
        prose = [line for line in body.splitlines() if not line.startswith("|")]
        self.assertNotRegex("\n".join(prose), r"\bEq\.")
        flat = " ".join(" ".join(prose).split())
        self.assertIsNone(re.search(r"(?:^|[.!?:] |\*\* )\(\d+\)", flat))
        for line in prose:
            with self.subTest(line=line[:40]):
                self.assertNotRegex(line, r"^\s*(?:- )?\(\d+\) (?!=)")

    def test_standard_terms(self):
        # Vectors, scalars, components and tangent-space normals, not arrows, numbers, parts and tilts; the one
        # arrow left is the dashed arrow drawn in Fig. 2
        text = without_maths(read_paper()).replace("dashed arrow", "")
        for pattern in (r"(?i)\btilt", r"(?i)\bquarter\b", r"(?i)\bvotes?\b", r"(?i)\bat right angles\b",
                        r"(?i)\blength 1\b", r"(?i)\bUV steps\b", r"(?i)\bslopes?\b", r"(?i)\barrows?\b"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, text))

    def test_blue_is_marked_untested(self):
        # What blue holds comes from the modding community, not from this paper's tests
        paragraphs = [p for p in re.split(r"\n\n+", read_paper().split(REFERENCES_HEADING)[0]) if "gloss" in p]
        self.assertTrue(paragraphs)
        for paragraph in paragraphs:
            with self.subTest(paragraph=paragraph[:60]):
                self.assertIn("modding community", paragraph)
                self.assertRegex(paragraph, r"not tested|did not test")

    def test_british_spelling(self):
        text = read_paper()
        for pattern in (r"(?i)\bcolor", r"(?i)counterclockwise", r"Acknowledgment",
                        r"(?i)\b[a-z]{3,}iz(?:e|es|ed|ing|ation)\b"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, text))


class TestToolNeutral(unittest.TestCase):
    """The paper names no tool, setting or release, except in the reference that cites ER Tangents' code."""

    SOURCE_ENTRY = "Add an ER Tangents import option"

    def text_without_source_entry(self):
        text = read_paper()
        entries = re.split(r"\n\n+", text.split(REFERENCES_HEADING)[1].strip())
        source = [entry for entry in entries if self.SOURCE_ENTRY in entry]
        self.assertEqual(len(source), 1)
        return text.replace(source[0], "")

    def test_fbximporter_is_named_only_in_its_reference(self):
        self.assertIn("FbxImporter", read_paper())
        self.assertNotIn("FbxImporter", self.text_without_source_entry())

    def test_no_tool_settings_releases_or_guide_links(self):
        text = self.text_without_source_entry()
        for pattern in (r"FLVER Prep", r"Prepare and Export", r"NORMAL_MAPS\.md", r"Transform", r"Mirror ticked",
                        r"Mirror unticked", r"\b1\.(?:3|6\.1|7\.0|10\.2|11\.0)\b", r"(?i)\b(?:un)?ticked\b",
                        r"(?i)\bimport option\b"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, text))

    def test_body_names_no_file_of_this_repository(self):
        # The scripts and results are cited through the repository reference, not named in the sections
        body = read_paper().split(REFERENCES_HEADING)[0]
        for pattern in (r"docs/", r"\b[\w-]+\.py\b", r"\b[\w-]+\.json\b"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, body))

    def test_paper_shows_the_paper_figures(self):
        images = re.findall(r"!\[[^\]]*\]\(\.\./figures/([^)]+)\)", read_paper())
        self.assertEqual(images, ["paper_normal_map_layout.svg", "tangent_frame.svg", "paper_axis_swap.svg",
                                  "paper_layout_test.svg", "paper_tangent_directions.svg", "paper_dome_tilts.svg", "paper_uv_triangle.svg",
                                  "paper_channel_changes.svg", "paper_ways_out_of_blender.svg"])


if __name__ == "__main__":
    unittest.main()
