# Tests for the clarifications to docs/paper/ER_NORMAL_MAPS.md made after a cold reading: what the paper says about the
# sign of d and the worked example's winding matches the committed survey and the formulas

import unittest

from test_paper import read_paper  # also puts docs/figures on sys.path

import frame_survey  # noqa: E402
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

    def test_the_paper_says_so(self):
        text = read_paper()
        example = text[text.index("**Worked example.**"):text.index("TABLE V")]
        self.assertIn("winds the other way from the game's", example)
        self.assertIn("$d > 0$ here on an\nunmirrored island", example)


if __name__ == "__main__":
    unittest.main()
