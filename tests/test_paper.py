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

import tangent_geometry as mf  # noqa: E402

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


class TestWording(unittest.TestCase):

    def test_no_dash_punctuation(self):
        text = without_maths(read_paper())
        self.assertNotIn("\u2014", text)
        self.assertNotIn("\u2013", text)
        self.assertNotRegex(text, r"(?<![-|])--(?![-|])")
        self.assertNotRegex(text, r"[A-Za-z,] - [A-Za-z]")

    def test_standard_terms(self):
        # Vectors, scalars, components and tangent-space normals, not arrows, numbers, parts and tilts; the one
        # arrow left is the dashed arrow drawn in Fig. 2
        text = without_maths(read_paper()).replace("dashed arrow", "")
        for pattern in (r"(?i)\btilt", r"(?i)\bquarter\b", r"(?i)\bvotes?\b", r"(?i)\bat right angles\b",
                        r"(?i)\blength 1\b", r"(?i)\bUV steps\b", r"(?i)\bslopes?\b", r"(?i)\barrows?\b"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, text))

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
                        r"Mirror unticked", r"\b1\.(?:3|6\.1|7\.0|10\.2|11\.0)\b"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, text))

    def test_paper_shows_the_paper_figures(self):
        images = re.findall(r"!\[[^\]]*\]\(\.\./figures/([^)]+)\)", read_paper())
        self.assertEqual(images, ["paper_normal_map_layout.svg", "tangent_frame.svg", "paper_tangent_directions.svg",
                                  "paper_dome_tilts.svg", "paper_ways_out_of_blender.svg"])


if __name__ == "__main__":
    unittest.main()
