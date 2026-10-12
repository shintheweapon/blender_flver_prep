# Tests for export.py: the FBX file holds the prepared copies as they are

import os
import tempfile
import unittest

import bpy
from mathutils import Vector

from read_fbx import read_meshes
from src import export, prepare
from test_prepare import Scene, close, close_normal


class ExportTests(unittest.TestCase):

    def setUp(self):
        self.scene = Scene()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = os.path.join(folder.name, 'out.fbx')

    def export(self, mirror_z=False, flip_faces=False):
        result = self.scene.run(mirror_z=mirror_z, flip_faces=flip_faces)
        count = export.export_collection(bpy.context, result.collection, self.path)
        return result, count, read_meshes(self.path)

    def test_vertices_are_the_copies_own(self):
        for mirror_z in (False, True):
            result, count, meshes = self.export(mirror_z=mirror_z)
            self.assertEqual(count, 2)
            for copy in result.meshes:
                written = meshes[copy.name].vertices
                self.assertEqual(len(written), len(copy.data.vertices), copy.name)
                for a, b in zip(written, copy.data.vertices):
                    self.assertTrue(close(a, b.co), (mirror_z, copy.name, a, b.co))

    def test_corner_order_and_normals_are_the_copies_own(self):
        for flip_faces in (False, True):
            result, _, meshes = self.export(mirror_z=True, flip_faces=flip_faces)
            copy = result.meshes[0]
            written = meshes[copy.name]
            self.assertEqual(written.corners, [l.vertex_index for l in copy.data.loops])
            self.assertEqual(len(written.normals), len(copy.data.loops))
            for a, b in zip(written.normals, copy.data.corner_normals):
                self.assertTrue(close_normal(a, b.vector), (flip_faces, a, tuple(b.vector)))

    def test_names_keep_the_suffix_and_clusters_name_the_bones(self):
        result, _, meshes = self.export()
        self.assertEqual(sorted(meshes), ['Body_fs', 'Hair_fs'])
        body, hair = result.meshes
        # Every vertex is weighted to one bone; clusters of other bones are empty
        self.assertEqual(meshes['Body_fs'].bones, {'Root': len(body.data.vertices), 'Child': 0})
        self.assertEqual(meshes['Hair_fs'].bones, {'Root': 0, 'Child': len(hair.data.vertices)})

    def test_selection_and_active_restored(self):
        self.scene.body.select_set(True)
        bpy.context.view_layer.objects.active = self.scene.body
        before = {o.name: o.select_get() for o in bpy.context.view_layer.objects}
        result = self.scene.run()
        export.export_collection(bpy.context, result.collection, self.path)
        for obj in bpy.context.view_layer.objects:
            self.assertEqual(obj.select_get(), before.get(obj.name, False), obj.name)
        self.assertIs(bpy.context.view_layer.objects.active, self.scene.body)

    def test_selection_restored_when_export_fails(self):
        result = self.scene.run()
        self.scene.body.select_set(True)
        with self.assertRaises(RuntimeError):
            export.export_collection(bpy.context, result.collection,
                                     os.path.join(self.path, 'missing', 'out.fbx'))
        self.assertTrue(self.scene.body.select_get())
        self.assertFalse(any(o.select_get() for o in result.collection.objects))

    def test_prepared_collection_found_from_original_or_copy(self):
        result = self.scene.run()
        self.assertIs(export.prepared_collection(self.scene.armature), result.collection)
        self.assertIs(export.prepared_collection(result.armature), result.collection)
        other = bpy.data.objects.new('Other', bpy.data.armatures.new('Other'))
        self.assertIsNone(export.prepared_collection(other))

    def test_option_tags_written(self):
        result = self.scene.run(mirror_z=True, flip_faces=False)
        self.assertTrue(result.collection[prepare.MIRROR_Z_KEY])
        self.assertFalse(result.collection[prepare.FLIP_FACES_KEY])


if __name__ == '__main__':
    unittest.main()
