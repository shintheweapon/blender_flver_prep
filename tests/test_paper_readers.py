# Tests for the clarifications to docs/paper/ER_NORMAL_MAPS.md made after a cold reading: what the paper says about the
# sign of d, the edge identity, the worked example's winding, the split of the layout test's exceptions, Fig. 4's
# caption and the description of Fig. 7 match the committed results, the formulas and the figure labels

import unittest

from test_paper import read_paper  # also puts docs/figures on sys.path

import frame_survey  # noqa: E402
import layout_results  # noqa: E402
import make_figures  # noqa: E402
import tangent_geometry as mf  # noqa: E402


def cross(a, b):
    """The cross product of two 3D vectors, by the paper's (2)."""
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    """The dot product of two vectors."""
    return sum(x * y for x, y in zip(a, b))


def held_by_sign(parts, cloth):
    """
    Share of corners where (9) holds, per sign of d, over the meshes of one kind.

    Parameters
    ----------
    parts : list of dict
        The survey, as ``frame_survey.load`` returns it.
    cloth : bool
        True for meshes whose material name contains "cloth", False for the others.

    Returns
    -------
    dict
        ``{"+": share, "-": share}``, each from 0 to 1.
    """
    totals = {"+": [0, 0], "-": [0, 0]}
    for part in parts:
        for mesh in part["meshes"]:
            if frame_survey.is_cloth(mesh["material"]) != cloth:
                continue
            for sign in totals:
                held, count = mesh["held"][sign]
                totals[sign][0] += held
                totals[sign][1] += count
    return {sign: held / count for sign, (held, count) in totals.items()}


class TestSignOfD(unittest.TestCase):
    """Section IV-B ties the sign of d to mirrored islands, and the survey agrees."""

    def section(self):
        text = read_paper()
        return text[text.index("### B. Vanilla Frames"):text.index("### C. The In-Game Test")]

    def test_the_paper_states_which_sign_is_mirrored(self):
        self.assertIn("$d > 0$ on mirrored islands and $d < 0$ on unmirrored", self.section())

    def test_the_paper_states_the_game_winding_behind_it(self):
        text = " ".join(self.section().split())
        self.assertIn(r"With the game's winding (III-C), $\vec{N}\cdot(\vec{e}_1\times\vec{e}_2) < 0$", text)

    def test_cloth_meshes_fail_only_where_d_is_positive(self):
        # cloth meshes keep W = -1, the unmirrored value, so (9) fails exactly on their mirrored corners
        share = held_by_sign(frame_survey.load(), cloth=True)
        self.assertLess(share["+"], 0.05)
        self.assertGreater(share["-"], 0.95)

    def test_other_meshes_hold_on_both_signs(self):
        share = held_by_sign(frame_survey.load(), cloth=False)
        self.assertGreater(min(share.values()), 0.95)


class TestWorkedExampleWinding(unittest.TestCase):
    """The worked example winds the other way from the game's, as the paper says."""

    POSITIONS = ((0, 0, 0), (2, 0, 0), (0, 0, 1))
    UVS = ((0, 0), (0.5, 0), (0, 0.25))
    NORMAL = (0, -1, 0)

    def test_edges_cross_along_the_normal(self):
        p0, p1, p2 = self.POSITIONS
        edges = cross(tuple(b - a for a, b in zip(p0, p1)), tuple(b - a for a, b in zip(p0, p2)))
        self.assertGreater(dot(self.NORMAL, edges), 0)

    def test_d_is_positive_on_an_unmirrored_island(self):
        d, du, dv = mf.uv_derivatives(self.POSITIONS, self.UVS)
        self.assertGreater(d, 0)
        # W = -1 by (9), the unmirrored value
        self.assertGreater(dot(self.NORMAL, cross(du, dv)), 0)

    def test_in_the_game_winding_d_is_negative_on_the_same_island(self):
        # vertices 1 and 2 swapped: the edges now cross opposite the normal, as on the game's models
        p0, p1, p2 = self.POSITIONS
        uv0, uv1, uv2 = self.UVS
        d, du, dv = mf.uv_derivatives((p0, p2, p1), (uv0, uv2, uv1))
        edges = cross(tuple(b - a for a, b in zip(p0, p2)), tuple(b - a for a, b in zip(p0, p1)))
        self.assertLess(dot(self.NORMAL, edges), 0)
        self.assertLess(d, 0)
        # W = -1 by (9) either way: the island is unmirrored
        self.assertGreater(dot(self.NORMAL, cross(du, dv)), 0)

    def test_the_paper_says_so(self):
        text = read_paper()
        example = text[text.index("**Worked example.**"):text.index("TABLE V")]
        self.assertIn("winds the other way from the game's", example)
        self.assertIn("$d > 0$ here on an\nunmirrored island", example)


class TestLayoutExceptions(unittest.TestCase):
    """Section IV-A splits the maps that disagree as the committed results do."""

    def test_split_of_the_exceptions_is_the_results(self):
        maps = layout_results.load()["maps"]
        inverted = sum(m["outcome"] == "directx-" for m in maps)
        swapped = sum(m["outcome"] in ("swapped+", "swapped-") for m in maps)
        text = read_paper()
        section = text[text.index("### A. The Integrability Test"):text.index("### B. Vanilla Frames")]
        self.assertIn(f"green inverted ({inverted} maps) or the swapped pairing ({swapped} maps)", section)


class TestDomeReflection(unittest.TestCase):
    """Fig. 7 and its guide twin describe the reflection about U = V as the geometry gives it."""

    def test_both_descriptions_name_the_other_diagonal_and_the_sideways_normals(self):
        for labels in (make_figures.GUIDE_LABELS, make_figures.PAPER_LABELS):
            with self.subTest(labels=labels.dome_title):
                self.assertIn("other diagonal turn inward", labels.dome_desc)
                self.assertIn("turn sideways", labels.dome_desc)

    def test_the_paper_text_citing_fig_7_says_so(self):
        text = " ".join(read_paper().split())
        self.assertIn("raised on the U = V diagonal, dented on the U = −V diagonal and lit from the side along U and V "
                      "(Fig. 7)", text)


class TestEdgeIdentity(unittest.TestCase):
    """The identity that ties the sign of d to the winding holds, and the paper states it."""

    TRIANGLES = (
        (((0, 0, 0), (2, 0, 0), (0, 0, 1)), ((0, 0), (0.5, 0), (0, 0.25))),
        (((0.1, -0.4, 0.3), (1.2, 0.5, -0.2), (-0.3, 0.9, 0.8)), ((0.2, 0.7), (0.9, 0.1), (0.4, 0.95))),
        (((1, 1, 1), (1, 2, 1), (2, 1, 3)), ((0.5, 0.5), (0.25, 0.5), (0.5, 0.0))),
    )

    def test_edges_cross_to_d_times_the_partial_derivatives(self):
        for positions, uvs in self.TRIANGLES:
            d, du, dv = mf.uv_derivatives(positions, uvs)
            p0, p1, p2 = positions
            edges = cross(tuple(b - a for a, b in zip(p0, p1)), tuple(b - a for a, b in zip(p0, p2)))
            for got, want in zip(edges, cross(du, dv)):
                self.assertAlmostEqual(got, d * want)

    def test_the_paper_states_it(self):
        text = read_paper()
        section = text[text.index("### B. Vanilla Frames"):text.index("### C. The In-Game Test")]
        self.assertIn(r"$\vec{e}_1\times\vec{e}_2 = d\,(\partial\vec{p}/\partial u\times\partial\vec{p}/\partial v)$",
                      " ".join(section.split()))


class TestLayoutFigureCaption(unittest.TestCase):
    """Fig. 4's caption names the three outcomes the figure draws."""

    def test_caption_names_every_outcome(self):
        text = " ".join(read_paper().split())
        caption = text[text.index("Fig. 4. "):text.index("**Impact on the implementation.**", text.index("Fig. 4. "))]
        for outcome in ("DirectX pairing with a positive or a negative correlation", "the swapped pairing"):
            with self.subTest(outcome=outcome):
                self.assertIn(outcome, caption)


if __name__ == "__main__":
    unittest.main()
