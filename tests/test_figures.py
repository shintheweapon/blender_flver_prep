# Tests for the figures of docs/NORMAL_MAPS.md: the committed SVGs are what the script writes, and the arrows
# follow the rules the page states

import os
import re
import sys
import unittest

FIGURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "figures")
if FIGURES_DIR not in sys.path:
    sys.path.insert(0, FIGURES_DIR)

import axes  # noqa: E402
import axis_swap_figure  # noqa: E402
import frame_checks  # noqa: E402
import frame_survey  # noqa: E402
import integrability  # noqa: E402
import layout_results  # noqa: E402
import make_figures  # noqa: E402
import paper_figures  # noqa: E402
import survey_parts  # noqa: E402
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
        figures = make_figures.build_all()
        paper = {name: content for name, content in figures.items()
                 if name.startswith("paper_") or name.endswith(".zh.svg")}
        self.assertEqual(sum(not name.endswith(".zh.svg") for name in paper), 9)
        self.assertEqual(sum(name.endswith(".zh.svg") for name in paper), 10)
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

    def test_swap_brings_up_to_plus_y_forward_to_minus_z_and_keeps_left(self):
        self.assertEqual(axes.apply(axes.BLENDER_TO_FLVER, (0.0, 0.0, 1.0)), (0.0, 1.0, 0.0))
        self.assertEqual(axes.apply(axes.BLENDER_TO_FLVER, (0.0, -1.0, 0.0)), (0.0, 0.0, -1.0))
        self.assertEqual(axes.apply(axes.BLENDER_TO_FLVER, (1.0, 0.0, 0.0)), (1.0, 0.0, 0.0))

    def test_rotation_brings_up_to_plus_y_and_forward_to_plus_z(self):
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
        got = [tuple(axes.character_axes(matrix)[key] for key in ("left", "up", "forward", "handedness"))
               for _, matrix in axis_swap_figure.AXIS_STAGES]
        self.assertEqual(got, expected)
        figure = make_figures.build_all()["paper_axis_swap.svg"]
        for left, up, forward, handedness in expected:
            with self.subTest(forward=forward):
                self.assertIn(f"{handedness.capitalize()}-handed", figure)
                self.assertIn(f"Forward {forward.replace('-', '−')}, up {up}, left side {left}", figure)


class TestAxisSwapAnimation(unittest.TestCase):
    """The animated panel of Fig. 3: the character's coordinates through the rotation about X, then Z negated."""

    @staticmethod
    def matrices_close(a, b):
        return all(abs(x - y) < 1e-9 for row_a, row_b in zip(a, b) for x, y in zip(row_a, row_b))

    def test_stages(self):
        fig = axis_swap_figure
        self.assertTrue(self.matrices_close(fig.stage_matrix(0.0), axes.IDENTITY))
        self.assertTrue(self.matrices_close(fig.stage_matrix(fig.ROTATE[1]), axes.ROTATE_X_MINUS_90))
        self.assertTrue(self.matrices_close(fig.stage_matrix(fig.NEGATE[0]), axes.ROTATE_X_MINUS_90))
        self.assertTrue(self.matrices_close(fig.stage_matrix(1.0), axes.BLENDER_TO_FLVER))

    def test_end_pose_is_flvers(self):
        fig = axis_swap_figure
        points = fig.character_points(fig.stage_matrix(1.0))
        up = tuple(h - p for h, p in zip(points["neck"], points["pelvis"]))
        forward = tuple(n - h for n, h in zip(points["nose"], points["head"]))
        left = tuple(a - b for a, b in zip(points["left_foot"], points["right_foot"]))
        self.assertEqual([axes.axis_name(v) for v in (left, up, forward)],
                         [axes.character_axes(axes.BLENDER_TO_FLVER)[k] for k in ("left", "up", "forward")])

    def test_stands_first_and_lies_at_the_end(self):
        fig = axis_swap_figure
        start = fig.character_points(fig.stage_matrix(0.0))
        end = fig.character_points(fig.stage_matrix(1.0))
        # Blender Z is up: standing, the head is above the pelvis; lying, they are level
        self.assertGreater(start["head"][2] - start["pelvis"][2], 50)
        self.assertAlmostEqual(end["head"][2], end["pelvis"][2])

    def test_rotation_keeps_lengths_and_the_negation_reverses_handedness(self):
        fig = axis_swap_figure
        base = fig.character_points(axes.IDENTITY)
        length = lambda pts, a, b: sum((x - y) ** 2 for x, y in zip(pts[a], pts[b])) ** 0.5
        for t in fig.frame_times():
            matrix = fig.stage_matrix(t)
            with self.subTest(t=t):
                if t <= fig.NEGATE[0]:
                    self.assertAlmostEqual(axes.determinant(matrix), 1.0)
                    pts = fig.character_points(matrix)
                    for a, b, _, _ in fig.SEGMENTS:
                        self.assertAlmostEqual(length(pts, a, b), length(base, a, b))
        self.assertAlmostEqual(axes.determinant(fig.stage_matrix(1.0)), -1.0)

    def test_svg_keyframes_and_steps(self):
        import re
        figure = make_figures.build_all()["paper_axis_swap_animated.svg"]
        animations = re.findall(r'<animate attributeName="[^"]+" values="([^"]*)" keyTimes="([^"]*)"[^>]*dur="(\d+)s"',
                                figure)
        self.assertTrue(animations)
        for values, times, duration in animations:
            self.assertEqual(len(values.split(";")), len(times.split(";")))
            self.assertEqual(int(duration), 30)
        headings = [f"{i + 1}. {heading}" for i, (heading, _) in enumerate(axis_swap_figure.STEPS)]
        positions = [figure.index(f">{h}<") for h in headings]
        self.assertEqual(positions, sorted(positions))

    def test_notation(self):
        import re
        figure = make_figures.build_all()["paper_axis_swap_animated.svg"]
        for label in ("+X", "+Y", "+Z"):
            self.assertIn(f">{label}<", figure)
        for label, _, _, _, _ in axis_swap_figure.LIVE_LABELS:
            with self.subTest(label=label):
                element = re.search(rf'<text [^>]*class="s halo"[^>]*>(.*?){label}</text>', figure)
                self.assertIsNotNone(element)
                self.assertIn('attributeName="x"', element.group(1))
                self.assertIn('attributeName="y"', element.group(1))
        for _, label in axis_swap_figure.LEGEND:
            self.assertIn(f">{label}<", figure)

    def test_nose_is_drawn_over_the_head(self):
        figure = make_figures.build_all()["paper_axis_swap_animated.svg"]
        head = figure.index(f'r="14" fill="{axis_swap_figure.BODY}"')
        nose_line = figure.index(f'stroke="{axis_swap_figure.FORWARD}"')
        nose_head = figure.index(f'<polygon points=')
        self.assertLess(head, nose_line)
        self.assertLess(head, nose_head)

    def test_forward_label_hides_while_the_nose_has_no_length(self):
        fig = axis_swap_figure
        middle = (fig.NEGATE[0] + fig.NEGATE[1]) / 2
        frame = {name: fig.to_screen(p) for name, p in fig.character_points(fig.stage_matrix(middle)).items()}
        self.assertLess(fig.nose_length(frame), fig.SHORT_NOSE)


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


class TestChannelChanges(unittest.TestCase):
    """The paper's channel-change figure: (20) and (21) read back as authored; the map as authored does not."""

    def test_changed_map_decodes_outward(self):
        for key in ("none", "mirror_z"):
            for direction, _, changed in paper_figures.channel_change_points(key):
                with self.subTest(key=key, direction=direction):
                    self.assertTrue(close(changed, tuple(paper_figures.DOME_TILT * c for c in direction)))

    def test_authored_map_decodes_as_without_the_change(self):
        for key in ("none", "mirror_z"):
            for direction, authored, _ in paper_figures.channel_change_points(key):
                with self.subTest(key=key, direction=direction):
                    tilt = tuple(paper_figures.DOME_TILT * c for c in direction)
                    self.assertTrue(close(authored, mf.decode(tilt, CASE[key])))

    def test_authored_map_is_rotated_or_reflected(self):
        for direction, authored, _ in paper_figures.channel_change_points("none"):
            self.assertAlmostEqual(mf.dot(authored, direction), 0.0)
        reflected = [mf.dot(a, d) for d, a, _ in paper_figures.channel_change_points("mirror_z")]
        self.assertTrue(any(v > 0.5 for v in reflected) and any(v < -0.5 for v in reflected))

    def test_figure_is_marked_derived(self):
        self.assertIn("not tested in game", make_figures.build_all()["paper_channel_changes.svg"])

    def test_lower_labels_clear_the_dome_arrows(self):
        # a 12 px label's box starts about 13 above its baseline; the arrows and their heads end above that
        figures = make_figures.build_all()
        for name in ("paper_channel_changes.svg", "paper_channel_changes.zh.svg"):
            svg = figures[name]
            labels = [float(y) for y, body in re.findall(r'<text[^>]*\by="([\d.]+)"[^>]*>([^<]*)</text>', svg)
                      if "(20)" in body or "(21)" in body]
            ends = [max(float(a), float(b))
                    for a, b in re.findall(r'<line[^>]*\by1="([\d.]+)"[^>]*\by2="([\d.]+)"', svg)]
            with self.subTest(name=name):
                self.assertEqual(len(labels), 2)
                for label in labels:
                    above = [end for end in ends if end < label]
                    self.assertGreaterEqual(label - 13 - max(above), 6)


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
        # Rows run along +V (row 0 at the top), columns along +U
        return integrability.correlation(np.gradient(red, axis=0), np.gradient(green, axis=1))

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


class TestLayoutTest(unittest.TestCase):
    """The layout test run on whole maps and tiles, and the committed results behind Fig. 4 and Section IV-A."""

    def test_directx_map_is_directx_positive(self):
        red, green = TestSlopeTest.height_field()
        pairing, directx, _ = integrability.test(red, green)
        self.assertEqual((pairing, directx > 0), (integrability.DIRECTX, True))
        self.assertEqual(integrability.test_map(red, green)["outcome"], "directx+")

    def test_swapped_map_is_swapped(self):
        # Red stores the V component and green the U component
        red, green = TestSlopeTest.height_field()
        self.assertEqual(integrability.test(green, red)[0], integrability.SWAPPED)

    def test_inverted_green_is_directx_negative(self):
        red, green = TestSlopeTest.height_field()
        self.assertEqual(integrability.test_map(red, 1 - green)["outcome"], "directx-")

    def test_both_channels_inverted_look_the_same_to_the_test(self):
        # The test fixes the pairing and green's sign relative to red, not the overall sign
        red, green = TestSlopeTest.height_field()
        original = integrability.test_map(red, green)
        inverted = integrability.test_map(1 - red, 1 - green)
        self.assertEqual(inverted["outcome"], original["outcome"])
        self.assertAlmostEqual(inverted["directx"], original["directx"])

    def test_flat_tiles_are_skipped_and_a_flat_map_is_untestable(self):
        import numpy as np
        flat = np.full((512, 256), 0.5)
        self.assertEqual(integrability.tiles(flat, flat)["skipped"], 2)
        result = integrability.test_map(flat, flat)
        self.assertEqual(result["outcome"], layout_results.UNTESTABLE)
        self.assertIsNone(result["directx"])

    def test_summary(self):
        tiles = {"directx+": 1, "directx-": 0, "swapped+": 0, "swapped-": 0, "skipped": 0}
        maps = [{"name": "WP_A_1_n.dds", "directx": 0.6, "swapped": 0.2, "outcome": "directx+", "tiles": tiles},
                {"name": "wp_a_2_n.dds", "directx": -0.4, "swapped": -0.1, "outcome": "directx-", "tiles": tiles},
                {"name": "WP_A_3_n.dds", "directx": None, "swapped": None, "outcome": "untestable", "tiles": tiles},
                {"name": "FG_A_1_n.dds", "directx": 0.2, "swapped": 0.3, "outcome": "swapped+", "tiles": tiles}]
        rows = layout_results.summary(maps)
        self.assertEqual([row["prefix"] for row in rows], ["WP", "FG"])
        self.assertEqual((rows[0]["tested"], rows[0]["untestable"]), (2, 1))
        self.assertEqual(rows[0]["count"]["directx+"], 1)
        self.assertAlmostEqual(rows[0]["directx_median"], 0.1)

    def test_committed_results_have_no_paths(self):
        for entry in layout_results.load()["maps"]:
            with self.subTest(name=entry["name"]):
                self.assertNotRegex(entry["name"], r"[\\/:]")

    def test_figure_bars_are_the_committed_counts(self):
        rows = layout_results.summary(layout_results.load()["maps"])
        for (prefix, shares, tested, untestable), row in zip(paper_figures.layout_bars(rows), rows):
            with self.subTest(prefix=prefix):
                self.assertEqual((prefix, tested, untestable), (row["prefix"], row["tested"], row["untestable"]))
                self.assertAlmostEqual(sum(shares), 1.0)
                self.assertAlmostEqual(shares[0] * tested, row["count"]["directx+"])
        figure = make_figures.build_all()["paper_layout_test.svg"]
        for row in rows:
            self.assertIn(f">{paper_figures.prefix_label(row['prefix'])}<", figure)


class TestFrameSurvey(unittest.TestCase):
    """The survey behind the paper's Section IV-B: per mesh, per prefix, cloth meshes and exceptions."""

    @staticmethod
    def mesh(material, mirrored=False, flip_w=False, mtd=None):
        uvs = [(-u, v) for u, v in EXAMPLE_UVS] if mirrored else list(EXAMPLE_UVS)
        frames = mf.build_frame(EXAMPLE_POSITIONS, [EXAMPLE_NORMAL] * 3, uvs, [(0, 1, 2)], NO_FALLBACK)
        vertices = [{"p": list(p), "n": list(EXAMPLE_NORMAL), "t": [list(t) + [-w if flip_w else w]], "uv": [list(uv)]}
                    for p, uv, (t, w) in zip(EXAMPLE_POSITIONS, uvs, frames)]
        return {"material": material, "mtd": "data\\" + (mtd or f"P[X]_{material}.matxml"), "vertices": vertices,
                "triangles": [0, 1, 2]}

    def test_frames_in_the_game_convention_hold_everywhere(self):
        part = frame_survey.part_survey("BD_M_0000", [self.mesh("Fabric"), self.mesh("Fabric", mirrored=True)])
        self.assertEqual(part["corners"], 6)
        self.assertTrue(part["w_exact"])
        self.assertEqual(part["held"], {"+": [3, 3], "-": [3, 3]})

    def test_flipped_w_fails_and_meshes_without_tangents_are_skipped(self):
        empty = {"material": "x", "vertices": [], "triangles": []}
        part = frame_survey.part_survey("BD_M_0000", [self.mesh("Fabric_Cloth", flip_w=True), empty])
        self.assertEqual([m["index"] for m in part["meshes"]], [0])
        self.assertEqual(part["held"]["+"], [0, 3])
        self.assertIsNone(frame_survey.part_survey("BD_M_0001", [empty]))

    def test_cloth_split_and_exceptions(self):
        parts = [frame_survey.part_survey("BD_M_0000", [self.mesh("Fabric"), self.mesh("Fabric_Cloth", flip_w=True)]),
                 frame_survey.part_survey("WP_A_0000", [self.mesh("Metal")])]
        split = frame_survey.by_cloth(parts)
        self.assertEqual((split["cloth"]["meshes"], split["cloth"]["parts"]), (1, 1))
        self.assertEqual(split["cloth"]["held"]["+"], [0, 3])
        self.assertEqual((split["other"]["meshes"], split["other"]["parts"]), (2, 2))
        groups = frame_survey.exceptions(parts)
        self.assertEqual([(g["material"], g["meshes"], g["failed"]) for g in groups],
                         [("Fabric_Cloth", [("BD_M_0000", 1)], 3)])
        rows = frame_survey.summary_by_prefix(parts)
        self.assertEqual([(r["prefix"], r["parts"], r["corners"]) for r in rows], [("BD", 1, 6), ("WP", 1, 3)])

    def test_material_file_is_stored_without_its_path(self):
        part = frame_survey.part_survey("BD_M_0000", [self.mesh("Fabric")])
        self.assertEqual(part["meshes"][0]["mtd"], "P[X]_Fabric.matxml")

    def test_mesh_behaviour(self):
        entry = lambda held, total: {"held": {"+": [held, total], "-": [0, 0]}}
        self.assertEqual(frame_survey.mesh_behaviour(entry(100, 100)), frame_survey.FOLLOWS)
        self.assertEqual(frame_survey.mesh_behaviour(entry(2, 100)), frame_survey.KEEPS)
        self.assertEqual(frame_survey.mesh_behaviour(entry(50, 100)), frame_survey.MIXED)
        self.assertIsNone(frame_survey.mesh_behaviour(entry(0, 0)))

    def test_cloth_rule(self):
        # The unmirrored UVs of the example give d > 0 corners, where (9) asks for W = +1
        parts = [frame_survey.part_survey("BD_M_0000", [
            self.mesh("Fabric"),
            self.mesh("Fabric_Cloth", flip_w=True),
            self.mesh("skirt_cloth", mtd="P[X]_Skirt.matxml", flip_w=True)])]
        rule = frame_survey.cloth_rule(parts)
        self.assertEqual(rule["counts"], {(False, frame_survey.FOLLOWS): 1, (True, frame_survey.KEEPS): 1,
                                          (False, frame_survey.KEEPS): 1})
        self.assertEqual(rule["name_and_file_differ"], 1)
        self.assertEqual(rule["file_right"], 0)
        self.assertEqual(rule["disagreeing"],
                         [("BD_M_0000", 2, "skirt_cloth", "P[X]_Skirt.matxml", frame_survey.KEEPS)])

    def test_misfits(self):
        parts = [frame_survey.part_survey("BD_M_0000", [
            self.mesh("Fabric"),
            self.mesh("Metal", flip_w=True),
            self.mesh("Fabric_Cloth", flip_w=False)])]
        found = frame_survey.misfits(parts)
        self.assertEqual((found["meshes"], found["corners"], found["small"]), (2, 6, 2))
        self.assertEqual(found["large_other_mixed"]["meshes"], 0)
        self.assertEqual(found["large_cloth_following"], [])

    def test_flver_paths_lists_one_file_per_name(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            for folder, name in (("b", "BD_M_0001.flver"), ("a", "bd_m_0001.flver"), ("a", "WP_A_0001.flver"),
                                 ("a", "notes.txt")):
                os.makedirs(os.path.join(root, folder), exist_ok=True)
                open(os.path.join(root, folder, name), "w").close()
            found = [os.path.relpath(p, root) for p in survey_parts.flver_paths(root)]
        self.assertEqual(found, [os.path.join("a", "bd_m_0001.flver"), os.path.join("a", "WP_A_0001.flver")])

    def test_committed_survey_has_no_paths(self):
        for part in frame_survey.load():
            with self.subTest(part=part["name"]):
                self.assertNotRegex(part["name"], r"[\\/:]")
                for mesh in part["meshes"]:
                    self.assertNotRegex(mesh["material"], r"^[A-Za-z]:|[\\/]")
                    self.assertNotRegex(mesh["mtd"], r"^[A-Za-z]:|[\\/]")


if __name__ == "__main__":
    unittest.main()
