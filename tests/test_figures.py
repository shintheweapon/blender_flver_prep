# Tests for the figures of docs/NORMAL_MAPS.md: the committed SVGs are what the script writes, and the arrows
# follow the rules the page states

import os
import sys
import unittest

FIGURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "figures")
if FIGURES_DIR not in sys.path:
    sys.path.insert(0, FIGURES_DIR)

import axes  # noqa: E402
import frame_checks  # noqa: E402
import make_figures  # noqa: E402
import paper_figures  # noqa: E402
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

    CHARTS = {"guide": route_chart.GUIDE_CHART, "paper": route_chart.PAPER_CHART}

    def test_every_label_fits_its_box(self):
        for name, chart in self.CHARTS.items():
            for box in chart.boxes:
                title, *lines = box.lines
                with self.subTest(chart=name, box=title):
                    widths = ([len(title) * self.TITLE_PX_PER_CHAR]
                              + [len(text) * self.LINE_PX_PER_CHAR for text in lines])
                    self.assertLessEqual(max(widths) + 2 * self.PADDING, box.width)

    def test_every_line_fits_its_box_height(self):
        for name, chart in self.CHARTS.items():
            for box in chart.boxes:
                with self.subTest(chart=name, box=box.lines[0]):
                    self.assertLessEqual(route_chart.text_block_height(len(box.lines)) + 2 * self.PADDING,
                                         box.height)

    def test_boxes_do_not_overlap_and_stay_inside_the_figure(self):
        for name, chart in self.CHARTS.items():
            boxes = chart.boxes
            for box in boxes:
                with self.subTest(chart=name, box=box.lines[0]):
                    self.assertGreaterEqual(box.x, 0)
                    self.assertGreaterEqual(box.y, 0)
                    self.assertLessEqual(box.x + box.width, route_chart.WIDTH)
                    self.assertLessEqual(box.y + box.height, chart.height)
            for i, a in enumerate(boxes):
                for b in boxes[i + 1:]:
                    apart = (a.x + a.width <= b.x or b.x + b.width <= a.x
                             or a.y + a.height <= b.y or b.y + b.height <= a.y)
                    self.assertTrue(apart, f"{name}: {a.lines[0]} overlaps {b.lines[0]}")

    def test_guide_chart_is_the_route_boxes(self):
        self.assertIs(route_chart.GUIDE_CHART.boxes, route_chart.ROUTE_BOXES)
        self.assertEqual(route_chart.GUIDE_CHART.height, route_chart.HEIGHT)


class TestPaperFigures(unittest.TestCase):
    """The paper's versions of the figures name no tool, setting or release, and use standard terms."""

    FORBIDDEN = (r"FbxImporter|FLVER Prep|Transform|Mirror ticked|Mirror unticked|\b1\.(?:3|6\.1|7\.0|10\.2|11\.0)\b"
                 r"|\b(?:[Uu]n)?ticked\b")

    def test_paper_figures_name_no_tool_setting_or_release(self):
        import re
        paper = {name: content for name, content in make_figures.build_all().items() if name.startswith("paper_")}
        self.assertEqual(len(paper), 6)
        for name, content in paper.items():
            with self.subTest(name=name):
                self.assertEqual(re.findall(self.FORBIDDEN, content), [])

    def test_paper_figures_use_standard_terms(self):
        import re
        for name, content in make_figures.build_all().items():
            if name.startswith("paper_"):
                with self.subTest(name=name):
                    self.assertEqual(re.findall(r"(?i)\btilt|\bquarter\b", content), [])

    def test_guide_figures_keep_the_settings(self):
        figures = make_figures.build_all()
        self.assertIn("1.11.0: Transform None", figures["fbximporter_tangents.svg"])
        self.assertIn("In 1.3 to 1.6.1", figures["fbximporter_tangents.svg"])
        self.assertIn("Red: the surface tilts towards +U", figures["normal_map_layout.svg"])


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


class TestAxisSwap(unittest.TestCase):
    """The swap from Blender into FLVER space (paper Section III-C) and the handedness of views (Section II-C)."""

    def test_rotation_keeps_handedness_and_the_swap_reverses_it(self):
        self.assertAlmostEqual(axes.determinant(axes.ROTATE_X_MINUS_90), 1.0)
        self.assertAlmostEqual(axes.determinant(axes.BLENDER_TO_FLVER), -1.0)

    def test_swap_brings_up_to_plus_y_front_to_minus_z_and_keeps_left(self):
        self.assertEqual(axes.apply(axes.BLENDER_TO_FLVER, (0.0, 0.0, 1.0)), (0.0, 1.0, 0.0))
        self.assertEqual(axes.apply(axes.BLENDER_TO_FLVER, (0.0, -1.0, 0.0)), (0.0, 0.0, -1.0))
        self.assertEqual(axes.apply(axes.BLENDER_TO_FLVER, (1.0, 0.0, 0.0)), (1.0, 0.0, 0.0))

    def test_rotation_brings_up_to_plus_y_and_front_to_plus_z(self):
        self.assertEqual(axes.apply(axes.ROTATE_X_MINUS_90, (0.0, 0.0, 1.0)), (0.0, 1.0, 0.0))
        self.assertEqual(axes.apply(axes.ROTATE_X_MINUS_90, (0.0, -1.0, 0.0)), (0.0, 0.0, 1.0))

    def test_screen_rule(self):
        # x right and y up: z out of the screen is right-handed, z into it left-handed
        self.assertEqual(axes.screen_handedness((1, 0, 0), (0, 1, 0), (0, 0, 1)), "right")
        self.assertEqual(axes.screen_handedness((1, 0, 0), (0, 1, 0), (0, 0, -1)), "left")
        self.assertEqual(axes.screen_handedness(*axes.BLENDER_FRONT_VIEW), "right")
        self.assertEqual(axes.screen_handedness(*axes.FLVER_FRONT_VIEW), "left")

    def test_axis_name(self):
        self.assertEqual(axes.axis_name((0.0, 0.0, -1.0)), "-Z")
        with self.assertRaises(ValueError):
            axes.axis_name((1.0, 1.0, 0.0))

    def test_figure_panels(self):
        expected = [("+X", "+Z", "-Y", "right"), ("+X", "+Y", "+Z", "right"), ("+X", "+Y", "-Z", "left")]
        got = [tuple(axes.character_axes(matrix)[key] for key in ("left", "up", "front", "handedness"))
               for _, matrix in paper_figures.AXIS_STAGES]
        self.assertEqual(got, expected)
        figure = make_figures.build_all()["paper_axis_swap.svg"]
        for left, up, front, handedness in expected:
            with self.subTest(front=front):
                self.assertIn(f"{handedness.capitalize()}-handed", figure)
                self.assertIn(f"Front {front.replace('-', '−')}, up {up}, left side {left}", figure)


class TestUvTriangle(unittest.TestCase):
    """Fig. 7 of the paper: the worked example in UV space and in game, seen from below."""

    def test_view_from_below_is_left_handed_like_flver(self):
        self.assertEqual(axes.screen_handedness(*axes.FLVER_BELOW_VIEW), "left")
        self.assertEqual(axes.screen_handedness(*axes.FLVER_BELOW_VIEW),
                         axes.screen_handedness(*axes.FLVER_FRONT_VIEW))

    def test_frame_is_the_worked_example(self):
        frame = paper_figures.example_frame()
        self.assertTrue(close(frame["dp_du"], (4, 0, 0)))
        self.assertTrue(close(frame["dp_dv"], (0, 0, 4)))
        self.assertTrue(close(frame["T"], (0, 0, 1)))
        self.assertEqual(frame["W"], -1)

    def test_drawn_directions_match_the_uv_panel(self):
        # On screen (right, down): T down like +V, B right like +U, N x T left, N out of the screen
        frame = paper_figures.example_frame()
        self.assertTrue(close(paper_figures.drawn(frame["T"]), (0, 1, 0)))
        self.assertTrue(close(paper_figures.drawn(frame["B"]), (1, 0, 0)))
        self.assertTrue(close(paper_figures.drawn(frame["N x T"]), (-1, 0, 0)))
        self.assertTrue(close(paper_figures.drawn(frame["N"]), (0, 0, 1)))
        for i, (u, v) in enumerate(paper_figures.EXAMPLE_UVS):
            with self.subTest(corner=i):
                right, down, _ = paper_figures.drawn(paper_figures.EXAMPLE_POSITIONS[i])
                self.assertTrue(close((right, down), (4 * u, 4 * v)))

    def test_figure_states_the_values(self):
        figure = make_figures.build_all()["paper_uv_triangle.svg"]
        self.assertIn("∂p/∂u = (4, 0, 0), ∂p/∂v = (0, 0, 4)", figure)
        self.assertIn("W = −1", figure)


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


class TestFrameChecks(unittest.TestCase):
    """The check of the paper's Section IV-B, on frames built in the game's convention."""

    def checks(self, uvs, tangents=None, triangles=((0, 1, 2),)):
        normals = [EXAMPLE_NORMAL] * 3
        if tangents is None:
            tangents = [tuple(t) + (w,) for t, w in mf.build_frame(EXAMPLE_POSITIONS, normals, uvs, triangles,
                                                                   NO_FALLBACK)]
        return frame_checks.frame_checks(EXAMPLE_POSITIONS, normals, uvs, triangles, tangents)

    def test_frames_in_the_game_convention_pass_on_both_uv_orientations(self):
        for uvs in (EXAMPLE_UVS, [(-u, v) for u, v in EXAMPLE_UVS]):
            corners = self.checks(uvs)
            self.assertEqual(len(corners), 3)
            for corner in corners:
                with self.subTest(uvs=uvs):
                    self.assertTrue(corner.w_rule)
                    self.assertAlmostEqual(corner.v_cos, 1.0)
                    self.assertAlmostEqual(corner.normal_dot, 0.0)
                    self.assertAlmostEqual(corner.length, 1.0)
        self.assertEqual({c.uv_sign for c in self.checks(EXAMPLE_UVS)}, {1})
        self.assertEqual({c.uv_sign for c in self.checks([(-u, v) for u, v in EXAMPLE_UVS])}, {-1})

    def test_flipped_w_breaks_the_rule(self):
        corners = self.checks(EXAMPLE_UVS, [(0.0, 0.0, 1.0, 1.0)] * 3)
        self.assertFalse(any(corner.w_rule for corner in corners))

    def test_tangent_along_u_is_orthogonal_to_v(self):
        corners = self.checks(EXAMPLE_UVS, [(1.0, 0.0, 0.0, -1.0)] * 3)
        for corner in corners:
            self.assertAlmostEqual(corner.v_cos, 0.0)

    def test_degenerate_triangles_are_skipped(self):
        tangents = [(0.0, 0.0, 1.0, -1.0)] * 3
        self.assertEqual(len(self.checks(EXAMPLE_UVS, tangents)), 3)
        self.assertEqual(self.checks(EXAMPLE_UVS, tangents, ((0, 0, 2),)), [])
        self.assertEqual(self.checks([(0.0, 0.0), (0.5, 0.0), (1.0, 0.0)], tangents), [])
        self.assertEqual(self.checks(EXAMPLE_UVS, NO_FALLBACK), [])

    def test_summarise(self):
        corners = self.checks(EXAMPLE_UVS) + self.checks(EXAMPLE_UVS, [(0.0, 0.0, 2.0, 1.0)] * 3)
        summary = frame_checks.summarise(corners)
        self.assertEqual(summary["w_values"], [-1, 1])
        self.assertTrue(close(summary["length"], (1.0, 2.0)))
        self.assertAlmostEqual(summary["normal_dot_99"], 0.0)
        self.assertAlmostEqual(summary["v_cos_median"], 1.0)
        self.assertAlmostEqual(summary["w_rule"], 0.5)
        self.assertEqual(summary["w_rule_by_uv_sign"][1], 0.5)
        self.assertIsNone(summary["w_rule_by_uv_sign"][-1])

    def test_summarise_needs_corners(self):
        with self.assertRaises(ValueError):
            frame_checks.summarise([])


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
