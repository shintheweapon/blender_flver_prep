# Tests for the figures of docs/NORMAL_MAPS.md: the committed SVGs are what the script writes, and the arrows
# follow the rules the page states

import os
import sys
import unittest

FIGURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "figures")
if FIGURES_DIR not in sys.path:
    sys.path.insert(0, FIGURES_DIR)

import make_figures  # noqa: E402
import tangent_geometry as mf  # noqa: E402

CASE = {case.key: case for case in mf.CASES}


def close(a, b):
    return all(abs(x - y) < 1e-6 for x, y in zip(a, b))


class TestCommittedFigures(unittest.TestCase):

    def test_committed_svgs_are_what_the_script_writes(self):
        for name, content in make_figures.build_all().items():
            with self.subTest(name=name):
                # Universal newlines: git may check the files out with CRLF line endings
                with open(os.path.join(FIGURES_DIR, name), encoding="utf-8") as file:
                    self.assertEqual(file.read(), content,
                                     "run python docs/figures/make_figures.py to rewrite it")


class TestTangentFrame(unittest.TestCase):

    def test_cross_product_follows_the_left_hand_rule(self):
        # N up, T towards the viewer: the right hand gives +x, the left hand -x
        self.assertEqual(mf.cross((0, 1, 0), (0, 0, 1)), (1, 0, 0))
        self.assertEqual(mf.cross_as_drawn((0, 1, 0), (0, 0, 1)), (-1, 0, 0))

    def test_unmirrored_island_has_w_minus_one(self):
        self.assertEqual(mf.vanilla_sign(False), -1)

    def test_mirrored_island_has_w_plus_one(self):
        self.assertEqual(mf.vanilla_sign(True), 1)

    def test_w_n_x_t_points_along_plus_u_on_both_islands(self):
        for mirrored in (False, True):
            with self.subTest(mirrored=mirrored):
                n_x_t = mf.cross_as_drawn(mf.NORMAL, mf.to_3d(mf.V, mirrored))
                w = mf.vanilla_sign(mirrored)
                self.assertTrue(close(tuple(w * c for c in n_x_t), mf.to_3d(mf.U, mirrored)))


class TestReadDirections(unittest.TestCase):

    def test_vanilla_reads_green_along_plus_v_and_red_along_plus_u(self):
        self.assertEqual(mf.read_directions(CASE["vanilla"]), ((0, 1), (1, 0)))

    def test_transform_none_reads_green_along_plus_u_and_red_along_minus_v(self):
        self.assertEqual(mf.read_directions(CASE["none"]), ((1, 0), (0, -1)))

    def test_mirror_z_reads_green_along_plus_u_and_red_along_plus_v(self):
        self.assertEqual(mf.read_directions(CASE["mirror_z"]), ((1, 0), (0, 1)))


class TestDome(unittest.TestCase):

    def test_vanilla_tilts_point_outward(self):
        for direction in mf.dome_points():
            self.assertTrue(close(mf.decode(direction, CASE["vanilla"]), direction))

    def test_transform_none_turns_each_tilt_a_quarter(self):
        for a, b in mf.dome_points():
            decoded = mf.decode((a, b), CASE["none"])
            self.assertTrue(close(decoded, (b, -a)))
            self.assertAlmostEqual(mf.dot(decoded, (a, b)), 0.0)

    def test_mirror_z_flips_each_tilt_across_the_diagonal(self):
        outward, inward = [], []
        for a, b in mf.dome_points():
            decoded = mf.decode((a, b), CASE["mirror_z"])
            self.assertTrue(close(decoded, (b, a)))
            along = mf.dot(decoded, (a, b))
            if along > 1e-6:
                outward.append((a, b))
            elif along < -1e-6:
                inward.append((a, b))
        # outward on the U = V diagonal, inward on the other; the tilts on the U and V axes come out sideways
        self.assertTrue(outward and all(abs(a - b) < 1e-6 for a, b in outward))
        self.assertTrue(inward and all(abs(a + b) < 1e-6 for a, b in inward))

    def test_animation_ends_at_the_decoded_tilts_and_frame(self):
        for case in mf.CASES:
            motion = mf.MOTION[case.key]
            with self.subTest(case=case.key):
                for direction in mf.dome_points():
                    self.assertTrue(close(mf.apply_motion(motion, direction), mf.decode(direction, case)))
                green, red = mf.read_directions(case)
                self.assertTrue(close(mf.apply_motion(motion, mf.V), green))
                self.assertTrue(close(mf.apply_motion(motion, mf.U), red))


if __name__ == "__main__":
    unittest.main()
