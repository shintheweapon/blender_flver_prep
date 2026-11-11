# Tests for the figures of docs/NORMAL_MAPS.md: the committed SVGs are what the script writes, and the arrows
# follow the rules the page states

import os
import sys
import unittest

FIGURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "figures")
if FIGURES_DIR not in sys.path:
    sys.path.insert(0, FIGURES_DIR)

import make_figures  # noqa: E402
import route_chart  # noqa: E402
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


class TestRouteChart(unittest.TestCase):

    # Generous estimates of rendered text width, so that a label passing here has room to spare in any common font
    TITLE_PX_PER_CHAR = 8.5
    LINE_PX_PER_CHAR = 7.5
    PADDING = 12

    def test_every_label_fits_its_box(self):
        for box in route_chart.ROUTE_BOXES:
            title, *lines = box.lines
            with self.subTest(box=title):
                widths = [len(title) * self.TITLE_PX_PER_CHAR] + [len(text) * self.LINE_PX_PER_CHAR for text in lines]
                self.assertLessEqual(max(widths) + 2 * self.PADDING, box.width)

    def test_every_line_fits_its_box_height(self):
        for box in route_chart.ROUTE_BOXES:
            with self.subTest(box=box.lines[0]):
                self.assertLessEqual(route_chart.text_block_height(len(box.lines)) + 2 * self.PADDING, box.height)

    def test_boxes_do_not_overlap_and_stay_inside_the_figure(self):
        boxes = route_chart.ROUTE_BOXES
        for box in boxes:
            self.assertGreaterEqual(box.x, 0)
            self.assertGreaterEqual(box.y, 0)
            self.assertLessEqual(box.x + box.width, route_chart.WIDTH)
            self.assertLessEqual(box.y + box.height, route_chart.HEIGHT)
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                apart = (a.x + a.width <= b.x or b.x + b.width <= a.x
                         or a.y + a.height <= b.y or b.y + b.height <= a.y)
                self.assertTrue(apart, f"{a.lines[0]} overlaps {b.lines[0]}")


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


# The worked example of the paper: one triangle, its UVs and its normal
EXAMPLE_POSITIONS = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 0.0, 1.0)]
EXAMPLE_UVS = [(0.0, 0.0), (0.5, 0.0), (0.0, 0.25)]
EXAMPLE_NORMAL = (0.0, -1.0, 0.0)
NO_FALLBACK = [(0.0, 0.0, 0.0, 1.0)] * 3


def w_rule(normal, dp_du, dp_dv):
    """W = -sign(N . (dp/du x dp/dv)), the rule measured on vanilla models."""
    return -1 if mf.dot(normal, mf.cross(dp_du, dp_dv)) > 0 else 1


class TestColourEncoding(unittest.TestCase):

    def test_half_values_store_no_tilt(self):
        self.assertTrue(close(mf.decode_colour(0.5, 0.5), (0.0, 0.0, 1.0)))

    def test_decoded_tilt_has_length_one(self):
        for red, green in ((0.9, 0.5), (0.2, 0.7), (0.65, 0.35)):
            with self.subTest(red=red, green=green):
                self.assertAlmostEqual(mf.dot(mf.decode_colour(red, green), mf.decode_colour(red, green)), 1.0)

    def test_encode_is_the_inverse_of_decode(self):
        for a, b in mf.dome_points():
            with self.subTest(tilt=(a, b)):
                x, y, _ = mf.decode_colour(*mf.encode_colour(0.6 * a, 0.6 * b))
                self.assertTrue(close((x, y), (0.6 * a, 0.6 * b)))


class TestWorkedExample(unittest.TestCase):

    def test_uv_derivatives(self):
        d, dp_du, dp_dv = mf.uv_derivatives(EXAMPLE_POSITIONS, EXAMPLE_UVS)
        self.assertAlmostEqual(d, 0.125)
        self.assertTrue(close(dp_du, (4.0, 0.0, 0.0)))
        self.assertTrue(close(dp_dv, (0.0, 0.0, 4.0)))

    def test_frame(self):
        [(t, w)] = mf.build_frame(EXAMPLE_POSITIONS, [EXAMPLE_NORMAL] * 3, EXAMPLE_UVS, [(0, 1, 2)], NO_FALLBACK)[:1]
        self.assertTrue(close(t, (0.0, 0.0, 1.0)))
        self.assertTrue(close(mf.cross(EXAMPLE_NORMAL, t), (-1.0, 0.0, 0.0)))
        self.assertEqual(w, -1)
        self.assertTrue(close(tuple(w * c for c in mf.cross(EXAMPLE_NORMAL, t)), (1.0, 0.0, 0.0)))

    def test_w_matches_the_vanilla_rule(self):
        _, dp_du, dp_dv = mf.uv_derivatives(EXAMPLE_POSITIONS, EXAMPLE_UVS)
        self.assertEqual(w_rule(EXAMPLE_NORMAL, dp_du, dp_dv), -1)

    def test_every_vertex_gets_the_same_frame(self):
        frames = mf.build_frame(EXAMPLE_POSITIONS, [EXAMPLE_NORMAL] * 3, EXAMPLE_UVS, [(0, 1, 2)], NO_FALLBACK)
        for t, w in frames:
            self.assertTrue(close(t, (0.0, 0.0, 1.0)))
            self.assertEqual(w, -1)


class TestBuildFrame(unittest.TestCase):

    def test_corner_order_does_not_change_the_frame(self):
        forward = mf.build_frame(EXAMPLE_POSITIONS, [EXAMPLE_NORMAL] * 3, EXAMPLE_UVS, [(0, 1, 2)], NO_FALLBACK)
        reversed_ = mf.build_frame(EXAMPLE_POSITIONS, [EXAMPLE_NORMAL] * 3, EXAMPLE_UVS, [(0, 2, 1)], NO_FALLBACK)
        for (t1, w1), (t2, w2) in zip(forward, reversed_):
            self.assertTrue(close(t1, t2))
            self.assertEqual(w1, w2)

    def test_mirrored_uvs_flip_w_and_keep_t(self):
        mirrored = [(-u, v) for u, v in EXAMPLE_UVS]
        [(t, w)] = mf.build_frame(EXAMPLE_POSITIONS, [EXAMPLE_NORMAL] * 3, mirrored, [(0, 1, 2)], NO_FALLBACK)[:1]
        _, dp_du, dp_dv = mf.uv_derivatives(EXAMPLE_POSITIONS, mirrored)
        self.assertTrue(close(t, (0.0, 0.0, 1.0)))
        self.assertEqual(w, 1)
        self.assertEqual(w_rule(EXAMPLE_NORMAL, dp_du, dp_dv), 1)

    def test_tangent_is_perpendicular_to_a_tilted_normal(self):
        normal = (0.0, -0.8, 0.6)
        [(t, _)] = mf.build_frame(EXAMPLE_POSITIONS, [normal] * 3, EXAMPLE_UVS, [(0, 1, 2)], NO_FALLBACK)[:1]
        self.assertAlmostEqual(mf.dot(t, normal), 0.0)
        self.assertAlmostEqual(mf.dot(t, t), 1.0)

    def test_vertex_without_triangles_keeps_its_fallback(self):
        positions = EXAMPLE_POSITIONS + [(5.0, 0.0, 0.0)]
        fallback = NO_FALLBACK + [(1.0, 0.0, 0.0, -0.5)]
        frames = mf.build_frame(positions, [EXAMPLE_NORMAL] * 4, EXAMPLE_UVS + [(1.0, 1.0)], [(0, 1, 2)], fallback)
        self.assertEqual(frames[3], ((1.0, 0.0, 0.0), -1))

    def test_triangle_without_uv_area_is_skipped(self):
        self.assertIsNone(mf.uv_derivatives(EXAMPLE_POSITIONS, [(0.0, 0.0), (0.5, 0.0), (1.0, 0.0)]))
        frames = mf.build_frame(EXAMPLE_POSITIONS, [EXAMPLE_NORMAL] * 3, [(0.0, 0.0), (0.5, 0.0), (1.0, 0.0)],
                                [(0, 1, 2)], [(0.0, 1.0, 0.0, 1.0)] * 3)
        self.assertEqual(frames, [((0.0, 1.0, 0.0), 1)] * 3)


class TestDecodeMatrices(unittest.TestCase):

    MATRICES = {"none": ((0, 1), (-1, 0)), "mirror_z": ((0, 1), (1, 0))}

    def test_matrices_equal_decode_at_every_dome_point(self):
        for key, ((m00, m01), (m10, m11)) in self.MATRICES.items():
            for a, b in mf.dome_points():
                with self.subTest(case=key, tilt=(a, b)):
                    self.assertTrue(close((m00 * a + m01 * b, m10 * a + m11 * b), mf.decode((a, b), CASE[key])))


class TestWorkaround(unittest.TestCase):

    def test_workaround_reads_back_as_authored(self):
        for setting in mf.WORKAROUND_SETTINGS:
            for a, b in mf.dome_points():
                with self.subTest(setting=setting, tilt=(a, b)):
                    red, green = mf.workaround(*mf.encode_colour(0.6 * a, 0.6 * b), setting)
                    x, y, _ = mf.decode_colour(red, green)
                    self.assertTrue(close(mf.decode((x, y), CASE[setting]), (0.6 * a, 0.6 * b)))

    def test_unknown_setting_is_refused(self):
        with self.assertRaises(ValueError):
            mf.workaround(0.5, 0.5, "mirror_x")


class TestSlopeTest(unittest.TestCase):
    """The layout test of the paper on a synthetic height field: dR/dv matches dG/du in the DirectX layout."""

    @staticmethod
    def correlation(red, green):
        import numpy as np
        dr_dv = np.gradient(red, axis=0)  # rows run along +V (row 0 at the top)
        dg_du = np.gradient(green, axis=1)  # columns run along +U
        detail = np.abs(dr_dv) + np.abs(dg_du)
        keep = detail > np.median(detail)  # the more detailed half of the pixels
        return float(np.corrcoef(dr_dv[keep], dg_du[keep])[0, 1])

    @staticmethod
    def height_field():
        import numpy as np
        size = 128
        v, u = np.mgrid[0:size, 0:size] / size
        height = (0.04 * np.sin(2 * np.pi * 3 * u) * np.cos(2 * np.pi * 2 * v)
                  + 0.08 * np.exp(-((u - 0.3) ** 2 + (v - 0.6) ** 2) / 0.01)
                  - 0.05 * np.exp(-((u - 0.7) ** 2 + (v - 0.25) ** 2) / 0.005))
        dh_dv, dh_du = np.gradient(height, 1.0 / size)
        scale = np.sqrt(1 + dh_du ** 2 + dh_dv ** 2)
        return (-dh_du / scale + 1) / 2, (-dh_dv / scale + 1) / 2

    def test_directx_layout_passes(self):
        red, green = self.height_field()
        self.assertGreater(self.correlation(red, green), 0.9)

    def test_inverted_green_fails(self):
        red, green = self.height_field()
        self.assertLess(self.correlation(red, 1 - green), -0.9)


if __name__ == "__main__":
    unittest.main()
