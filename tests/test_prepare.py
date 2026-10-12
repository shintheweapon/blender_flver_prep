# Tests for prepare.py: the converted copy of an armature and its meshes

import unittest
from math import radians

import bpy
from mathutils import Matrix, Vector

import helpers
from src import prepare

TOLERANCE = 1e-5
# Blender stores custom normals relative to each face; a normal pointing against
# its face's winding (Mirror Z, Flip Faces) comes back within about 5e-5
NORMAL_TOLERANCE = 1e-4
BONES = [('Root', None, (0, 0, 0), (0, 0, 1)), ('Child', 'Root', (0, 0, 1), (0.3, 0.2, 1.8))]


def close(a, b, tolerance=TOLERANCE):
    """True when two vectors match within ``tolerance``."""
    return (Vector(a) - Vector(b)).length < tolerance


def close_normal(a, b):
    """True when two normals match within NORMAL_TOLERANCE."""
    return close(a, b, NORMAL_TOLERANCE)


class Scene:
    """A posed armature, one parented mesh, one modifier-only mesh with Subdivision."""

    def __init__(self):
        helpers.new_scene()
        self.material = bpy.data.materials.new('Skin')
        self.armature = helpers.make_armature(
            BONES, matrix=helpers.transform((1, 2, 3), (10, 20, 30)))
        self.body = helpers.make_skinned_mesh(
            'Body', self.armature, 'Root',
            matrix=helpers.transform((0.5, -1, 2), (30, -45, 60), (1, 2, 0.5)))
        self.body.data.materials.append(self.material)
        self.hair = helpers.make_skinned_mesh(
            'Hair', self.armature, 'Child', parented=False,
            matrix=helpers.transform((0, 0, 1)))
        self.hair.modifiers.new('Subdivision', 'SUBSURF').levels = 1
        # A posed bone: the copies must still use the rest pose
        self.armature.pose.bones['Root'].rotation_mode = 'XYZ'
        self.armature.pose.bones['Root'].rotation_euler = (radians(40), 0, 0)
        bpy.context.view_layer.update()

    def run(self, mirror_z=False, flip_faces=False):
        return prepare.prepare_copy(bpy.context, self.armature, mirror_z, flip_faces)


class ConversionMatrixTests(unittest.TestCase):

    def test_axis_conversion(self):
        self.assertTrue(close(prepare.conversion_matrix(False) @ Vector((1, 2, 3)), (1, 3, -2)))

    def test_mirror_z_gives_flver_axes(self):
        self.assertTrue(close(prepare.conversion_matrix(True) @ Vector((1, 2, 3)), (1, 3, 2)))


class FlippedCornerOrderTests(unittest.TestCase):

    def test_first_corner_kept_rest_reversed(self):
        self.assertEqual(prepare.flipped_corner_order([0, 3], [3, 4]), [0, 2, 1, 3, 6, 5, 4])

    def test_matches_blender_flip_normals(self):
        mesh = bpy.data.meshes.new('q')
        mesh.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (2, 0, 0)], [],
                         [(0, 1, 2, 3), (1, 4, 2)])
        before = [loop.vertex_index for loop in mesh.loops]
        order = prepare.flipped_corner_order((p.loop_start for p in mesh.polygons),
                                             (p.loop_total for p in mesh.polygons))
        mesh.flip_normals()
        self.assertEqual([loop.vertex_index for loop in mesh.loops], [before[i] for i in order])
        bpy.data.meshes.remove(mesh)


class PrepareCopyTests(unittest.TestCase):

    def setUp(self):
        self.scene = Scene()

    def expected_points(self, obj, mirror_z):
        """World coordinates of the original (rest pose), through the conversion matrix."""
        matrix = prepare.conversion_matrix(mirror_z) @ obj.matrix_world
        return [matrix @ v.co for v in obj.data.vertices]

    def test_armature_meshes_found_by_parent_and_modifier(self):
        found = prepare.armature_meshes(self.scene.armature, bpy.context.scene.objects)
        self.assertEqual([o.name for o in found], ['Body', 'Hair'])

    def test_vertices_are_converted_world_coordinates(self):
        for mirror_z in (False, True):
            result = self.scene.run(mirror_z=mirror_z)
            body = result.meshes[0]
            self.assertEqual(body.name, 'Body_fs')
            got = [v.co for v in body.data.vertices]
            for a, b in zip(got, self.expected_points(self.scene.body, mirror_z)):
                self.assertTrue(close(a, b), (mirror_z, a, b))

    def test_copies_have_identity_transforms(self):
        result = self.scene.run()
        for obj in [result.armature] + result.meshes:
            self.assertEqual(obj.matrix_world, Matrix.Identity(4), obj.name)

    def test_normals_follow_the_matrix_and_mirror_keeps_corner_order(self):
        source = self.scene.body
        original = [Vector(c.vector) for c in source.data.corner_normals]
        for mirror_z in (False, True):
            body = self.scene.run(mirror_z=mirror_z).meshes[0]
            full = prepare.conversion_matrix(mirror_z) @ source.matrix_world
            normal_matrix = full.to_3x3().inverted().transposed()
            self.assertEqual([l.vertex_index for l in body.data.loops],
                             [l.vertex_index for l in source.data.loops])
            for got, n in zip(body.data.corner_normals, original):
                self.assertTrue(close_normal(got.vector, (normal_matrix @ n).normalized()), mirror_z)

    def test_mirror_z_negates_z_of_positions_and_normals(self):
        plain = [(v.co.copy()) for v in self.scene.run().meshes[0].data.vertices]
        plain_n = [Vector(c.vector) for c in self.scene.run().meshes[0].data.corner_normals]
        mirrored = self.scene.run(mirror_z=True).meshes[0].data
        for a, b in zip(mirrored.vertices, plain):
            self.assertTrue(close(a.co, (b.x, b.y, -b.z)))
        for a, b in zip(mirrored.corner_normals, plain_n):
            self.assertTrue(close_normal(a.vector, (b.x, b.y, -b.z)))

    def test_flip_faces_reverses_corners_and_normals_follow(self):
        plain = self.scene.run().meshes[0].data
        plain_loops = [l.vertex_index for l in plain.loops]
        plain_n = [Vector(c.vector) for c in plain.corner_normals]
        flipped = self.scene.run(flip_faces=True).meshes[0].data
        order = prepare.flipped_corner_order((p.loop_start for p in flipped.polygons),
                                             (p.loop_total for p in flipped.polygons))
        self.assertEqual([l.vertex_index for l in flipped.loops], [plain_loops[i] for i in order])
        for got, i in zip(flipped.corner_normals, order):
            self.assertTrue(close_normal(got.vector, plain_n[i]))

    def test_rest_pose_used_and_pose_restored(self):
        self.scene.run()
        self.assertEqual(self.scene.armature.data.pose_position, 'POSE')
        # The posed original deforms; the copy matched rest coordinates above,
        # so check the original really is posed away from rest
        evaluated = self.scene.body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        moved = any(not close(a.co, b.co) for a, b in
                    zip(evaluated.data.vertices, self.scene.body.data.vertices))
        self.assertTrue(moved)

    def test_subdivision_baked_and_vertex_groups_kept(self):
        hair = self.scene.run().meshes[1]
        self.assertGreater(len(hair.data.vertices), len(self.scene.hair.data.vertices))
        self.assertEqual([g.name for g in hair.vertex_groups], ['Child'])
        self.assertTrue(all(len(v.groups) == 1 and abs(v.groups[0].weight - 1.0) < TOLERANCE
                            for v in hair.data.vertices))
        self.assertEqual(hair.modifiers[0].type, 'ARMATURE')
        self.assertEqual(len(hair.modifiers), 1)

    def test_materials_are_shared(self):
        body = self.scene.run().meshes[0]
        self.assertIs(body.material_slots[0].material, self.scene.material)

    def test_armature_copy_bones(self):
        result = self.scene.run(mirror_z=True)
        matrix = prepare.conversion_matrix(True) @ self.scene.armature.matrix_world
        source = self.scene.armature.data.bones
        copy = result.armature.data.bones
        self.assertEqual([b.name for b in copy], [b.name for b in source])
        for a, b in zip(copy, source):
            self.assertTrue(close(a.head_local, matrix @ b.head_local), a.name)
            self.assertTrue(close(a.tail_local, matrix @ b.tail_local), a.name)
        self.assertEqual(result.meshes[0].parent, result.armature)
        self.assertEqual(result.meshes[0].modifiers[0].object, result.armature)

    def test_collection_holds_only_the_copies(self):
        result = self.scene.run()
        self.assertEqual(result.collection.name, 'Armature_fs')
        self.assertEqual(result.collection[prepare.SOURCE_KEY], 'Armature')
        self.assertIn(result.collection, list(bpy.context.scene.collection.children))
        self.assertEqual(sorted(o.name for o in result.collection.objects),
                         ['Armature_fs', 'Body_fs', 'Hair_fs'])

    def test_rerun_replaces_previous_copy(self):
        self.scene.run()
        counts = (len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.armatures),
                  len(bpy.data.collections))
        result = self.scene.run(mirror_z=True)
        self.assertEqual((len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.armatures),
                          len(bpy.data.collections)), counts)
        self.assertEqual(result.collection.name, 'Armature_fs')
        self.assertEqual(sorted(o.name for o in result.collection.objects),
                         ['Armature_fs', 'Body_fs', 'Hair_fs'])

    def test_originals_selection_and_active_unchanged(self):
        self.scene.body.select_set(True)
        bpy.context.view_layer.objects.active = self.scene.body
        before = {o.name: (o.matrix_world.copy(), o.select_get()) for o in bpy.context.scene.objects}
        coords = [v.co.copy() for v in self.scene.body.data.vertices]
        self.scene.run(mirror_z=True, flip_faces=True)
        for name, (matrix, selected) in before.items():
            obj = bpy.data.objects[name]
            self.assertEqual(obj.matrix_world, matrix, name)
            self.assertEqual(obj.select_get(), selected, name)
        self.assertIs(bpy.context.view_layer.objects.active, self.scene.body)
        self.assertEqual([v.co for v in self.scene.body.data.vertices], coords)
        self.assertEqual(len(self.scene.body.modifiers), 1)


if __name__ == '__main__':
    unittest.main()
