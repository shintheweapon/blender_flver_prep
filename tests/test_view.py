# Tests for view.py and the Y-Up View and Roll View commands: the fixed views of
# the Y-up copies, the roll, and which side the copy's face is on

import math
import unittest

import bpy
from mathutils import Quaternion, Vector

from src import operator, prefs, view
from test_operator import enable
from test_prepare import Scene

TOLERANCE = 1e-6
# Expected world directions of (screen right, screen up, towards the viewer)
EXPECTED = {
    ('NEG_Z', 'Y_UP'): ((-1, 0, 0), (0, 1, 0), (0, 0, -1)),
    ('POS_Z', 'Y_UP'): ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    ('NEG_X', 'Y_UP'): ((0, 0, 1), (0, 1, 0), (-1, 0, 0)),
    ('POS_X', 'Y_UP'): ((0, 0, -1), (0, 1, 0), (1, 0, 0)),
    ('NEG_X', 'Z_DOWN'): ((0, 1, 0), (0, 0, -1), (-1, 0, 0)),
    ('POS_X', 'Z_DOWN'): ((0, -1, 0), (0, 0, -1), (1, 0, 0)),
    ('POS_Y', 'Y_UP'): ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
    ('NEG_Y', 'Y_UP'): ((-1, 0, 0), (0, 0, -1), (0, -1, 0)),
}


def same(a: Quaternion, b: Quaternion) -> bool:
    """Whether two quaternions give the same rotation (q and -q do)."""
    return abs(abs(a.dot(b)) - 1.0) < TOLERANCE


def half_turn(rotation: Quaternion, column: int) -> Quaternion:
    """The view turned half a turn about one of its own screen axes (0 right, 1 up)."""
    axis = rotation.to_matrix().col[column]
    return Quaternion(axis, math.pi) @ rotation


class ViewRotationTests(unittest.TestCase):

    def test_screen_axes_point_where_the_table_says(self):
        for (side, side_up), axes in EXPECTED.items():
            matrix = view.view_rotation(side, side_up).to_matrix()
            for column, expected in enumerate(axes):
                with self.subTest(side=side, side_up=side_up, column=column):
                    self.assertLess((matrix.col[column] - Vector(expected)).length, TOLERANCE)

    def test_rotations_have_no_mirror(self):
        for side, side_up in EXPECTED:
            with self.subTest(side=side, side_up=side_up):
                self.assertAlmostEqual(view.view_rotation(side, side_up).to_matrix().determinant(),
                                       1.0, places=6)

    def test_z_down_changes_only_the_x_sides(self):
        for side in ('NEG_Z', 'POS_Z', 'POS_Y', 'NEG_Y'):
            with self.subTest(side=side):
                self.assertTrue(same(view.view_rotation(side, 'Z_DOWN'), view.view_rotation(side)))

    def test_opposite_views_are_half_a_turn_apart(self):
        # Back from front and right from left about the screen's up, bottom
        # from top about the screen's right, as Blender's own views
        pairs = ((('NEG_Z', 'Y_UP'), ('POS_Z', 'Y_UP'), 1),
                 (('NEG_X', 'Y_UP'), ('POS_X', 'Y_UP'), 1),
                 (('NEG_X', 'Z_DOWN'), ('POS_X', 'Z_DOWN'), 1),
                 (('POS_Y', 'Y_UP'), ('NEG_Y', 'Y_UP'), 0))
        for first, second, column in pairs:
            with self.subTest(first=first, second=second):
                turned = half_turn(view.view_rotation(*first), column)
                self.assertTrue(same(turned, view.view_rotation(*second)))

    def test_neg_z_is_bottom_view_rolled_half_a_turn(self):
        # Ctrl+Numpad 7 gives Blender's Bottom view, (0, 1, 0, 0); rolling it 180
        # degrees turns about the view axis (the view's own Z)
        bottom = Quaternion((0.0, 1.0, 0.0, 0.0))
        rolled = bottom @ Quaternion((0.0, 0.0, 1.0), math.pi)
        self.assertLess(rolled.rotation_difference(view.view_rotation('NEG_Z')).angle, TOLERANCE)

    def test_unknown_side(self):
        with self.assertRaises(KeyError):
            view.view_rotation('BACK')


class RollTests(unittest.TestCase):

    def test_roll_right_turns_the_picture_clockwise(self):
        # Left with Y up, rolled right: +Z goes from the right to the bottom,
        # which is Left with Side Up set to Z-Down
        rolled = view.rolled(view.view_rotation('NEG_X'), 'RIGHT')
        self.assertTrue(same(rolled, view.view_rotation('NEG_X', 'Z_DOWN')))

    def test_roll_left_undoes_roll_right(self):
        start = view.view_rotation('POS_Y')
        self.assertTrue(same(view.rolled(view.rolled(start, 'RIGHT'), 'LEFT'), start))

    def test_four_rolls_return_to_the_start(self):
        for direction in ('LEFT', 'RIGHT'):
            rotation = view.view_rotation('NEG_Z')
            for _ in range(4):
                rotation = view.rolled(rotation, direction)
            with self.subTest(direction=direction):
                self.assertTrue(same(rotation, view.view_rotation('NEG_Z')))

    def test_roll_keeps_the_viewing_axis(self):
        start = view.view_rotation('POS_X')
        rolled = view.rolled(start, 'LEFT')
        self.assertLess((rolled.to_matrix().col[2] - start.to_matrix().col[2]).length, TOLERANCE)

    def test_unknown_direction(self):
        with self.assertRaises(ValueError):
            view.rolled(view.view_rotation('NEG_Z'), 'UP')


class FaceSideTests(unittest.TestCase):

    def test_face_side(self):
        self.assertEqual(view.face_side(False), 'POS_Z')
        self.assertEqual(view.face_side(True), 'NEG_Z')


class MirroredForTests(unittest.TestCase):

    def setUp(self):
        self.scene = Scene()
        enable(self)
        self.options = prefs.get(bpy.context)

    def test_without_a_copy_the_option_is_used(self):
        bpy.context.view_layer.objects.active = self.scene.armature
        for mirror_z in (False, True):
            self.options.mirror_z = mirror_z
            with self.subTest(mirror_z=mirror_z):
                self.assertIs(operator.mirrored_for(bpy.context), mirror_z)

    def test_the_copy_wins_over_the_option(self):
        for made_with in (False, True):
            result = self.scene.run(mirror_z=made_with)
            self.options.mirror_z = not made_with
            for active in (self.scene.armature, result.armature):
                bpy.context.view_layer.objects.active = active
                with self.subTest(made_with=made_with, active=active.name):
                    self.assertIs(operator.mirrored_for(bpy.context), made_with)

    def test_no_active_object(self):
        bpy.context.view_layer.objects.active = None
        self.options.mirror_z = True
        self.assertTrue(operator.mirrored_for(bpy.context))


class ViewCommandTests(unittest.TestCase):

    def setUp(self):
        enable(self)

    def test_need_a_3d_viewport(self):
        # Background Blender has no 3D Viewport in its context
        self.assertIsNone(bpy.context.space_data)
        self.assertFalse(bpy.ops.fs_export_prep.y_up_view.poll())
        self.assertFalse(bpy.ops.fs_export_prep.roll_view.poll())


if __name__ == '__main__':
    unittest.main()
