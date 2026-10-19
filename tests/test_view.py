# Tests for view.py and the Y-Up View command: the fixed views of the Y-up copies

import math
import unittest

import bpy
from mathutils import Quaternion, Vector

from src import view
from test_operator import enable

TOLERANCE = 1e-6
# Expected world directions of (screen right, screen up, towards the viewer)
EXPECTED = {
    'FRONT': ((-1, 0, 0), (0, 1, 0), (0, 0, -1)),
    'SIDE': ((0, 0, 1), (0, 1, 0), (-1, 0, 0)),
    'TOP': ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
}


class ViewRotationTests(unittest.TestCase):

    def test_screen_axes_point_where_the_table_says(self):
        for side, axes in EXPECTED.items():
            matrix = view.view_rotation(side).to_matrix()
            for column, expected in enumerate(axes):
                with self.subTest(side=side, column=column):
                    self.assertLess((matrix.col[column] - Vector(expected)).length, TOLERANCE)

    def test_rotations_have_no_mirror(self):
        for side in view.VIEWS:
            with self.subTest(side=side):
                self.assertAlmostEqual(view.view_rotation(side).to_matrix().determinant(), 1.0,
                                       places=6)

    def test_front_is_bottom_view_rolled_half_a_turn(self):
        # Ctrl+Numpad 7 gives Blender's Bottom view, (0, 1, 0, 0); rolling it 180
        # degrees turns about the view axis (the view's own Z)
        bottom = Quaternion((0.0, 1.0, 0.0, 0.0))
        rolled = bottom @ Quaternion((0.0, 0.0, 1.0), math.pi)
        self.assertLess(rolled.rotation_difference(view.view_rotation('FRONT')).angle, TOLERANCE)

    def test_unknown_side(self):
        with self.assertRaises(KeyError):
            view.view_rotation('BACK')


class YUpViewCommandTests(unittest.TestCase):

    def setUp(self):
        enable(self)

    def test_needs_a_3d_viewport(self):
        # Background Blender has no 3D Viewport in its context
        self.assertIsNone(bpy.context.space_data)
        self.assertFalse(bpy.ops.fs_fbx_tools.y_up_view.poll())


if __name__ == '__main__':
    unittest.main()
