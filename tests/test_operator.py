# End-to-end tests: register the add-on and run Prepare Copy

import unittest

import bpy

import helpers
import src
from src import prefs
from test_prepare import Scene

PACKAGE = src.__name__


def enable(test: unittest.TestCase) -> None:
    """Register the add-on with a preferences entry, as Blender does when it is enabled."""
    addons = bpy.context.preferences.addons
    if PACKAGE not in addons.keys():
        addons.new().module = PACKAGE
    src.register()

    def disable():
        src.unregister()
        if PACKAGE in addons.keys():
            addons.remove(addons[PACKAGE])
    test.addCleanup(disable)


class PrepareCopyOperatorTests(unittest.TestCase):

    def setUp(self):
        self.scene = Scene()
        enable(self)
        bpy.context.view_layer.objects.active = self.scene.armature

    def test_options_default_off(self):
        options = prefs.get(bpy.context)
        self.assertFalse(options.mirror_z)
        self.assertFalse(options.flip_faces)

    def test_prepares_the_collection(self):
        self.assertEqual(bpy.ops.fs_fbx_tools.prepare_copy(), {'FINISHED'})
        collection = bpy.data.collections['Armature_fs']
        self.assertEqual(sorted(o.name for o in collection.objects),
                         ['Armature_fs', 'Body_fs', 'Hair_fs'])

    def test_uses_the_mirror_z_option(self):
        bpy.ops.fs_fbx_tools.prepare_copy()
        plain = [v.co.copy() for v in bpy.data.objects['Body_fs'].data.vertices]
        prefs.get(bpy.context).mirror_z = True
        bpy.ops.fs_fbx_tools.prepare_copy()
        mirrored = [v.co for v in bpy.data.objects['Body_fs'].data.vertices]
        for a, b in zip(mirrored, plain):
            self.assertAlmostEqual(a.z, -b.z, places=5)

    def test_uses_the_flip_faces_option(self):
        bpy.ops.fs_fbx_tools.prepare_copy()
        plain = [l.vertex_index for l in bpy.data.objects['Body_fs'].data.loops]
        prefs.get(bpy.context).flip_faces = True
        bpy.ops.fs_fbx_tools.prepare_copy()
        flipped = [l.vertex_index for l in bpy.data.objects['Body_fs'].data.loops]
        self.assertEqual(flipped[:3], [plain[0], plain[2], plain[1]])

    def test_refuses_without_an_armature(self):
        bpy.context.view_layer.objects.active = self.scene.body
        with self.assertRaisesRegex(RuntimeError, 'Select an armature first'):
            bpy.ops.fs_fbx_tools.prepare_copy()

    def test_refuses_an_armature_without_meshes(self):
        lonely = helpers.make_armature([('Root', None, (0, 0, 0), (0, 0, 1))], name='Lonely')
        bpy.context.view_layer.objects.active = lonely
        with self.assertRaisesRegex(RuntimeError, 'Lonely has no meshes'):
            bpy.ops.fs_fbx_tools.prepare_copy()

    def test_refuses_outside_object_mode(self):
        bpy.ops.object.mode_set(mode='POSE')
        try:
            with self.assertRaisesRegex(RuntimeError, 'Switch to Object Mode first'):
                bpy.ops.fs_fbx_tools.prepare_copy()
        finally:
            bpy.ops.object.mode_set(mode='OBJECT')

    def test_unregister_removes_command_and_panel(self):
        src.unregister()
        try:
            self.assertFalse(hasattr(bpy.types, 'FS_FBX_TOOLS_OT_prepare_copy'))
            self.assertFalse(hasattr(bpy.types, 'FS_FBX_TOOLS_PT_main'))
        finally:
            src.register()


if __name__ == '__main__':
    unittest.main()
