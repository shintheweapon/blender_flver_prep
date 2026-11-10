# Tests for Remove Vertex Colors: the meshes' Color Attributes are removed

import unittest

import bpy

import helpers
from src import colors, prefs
from test_operator import enable


def mesh_with_colors(name: str, location=(0.0, 0.0, 0.0), render: str = "Corner Float") -> bpy.types.Object:
    """
    Add a triangle mesh object with four color attributes, one per domain and
    type, and ``render`` marked as the render color.

    Returns
    -------
    bpy.types.Object
        The object, linked to the scene and selected.
    """
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    for attr, data_type, domain in (("Point Byte", 'BYTE_COLOR', 'POINT'),
                                    ("Point Float", 'FLOAT_COLOR', 'POINT'),
                                    ("Corner Byte", 'BYTE_COLOR', 'CORNER'),
                                    ("Corner Float", 'FLOAT_COLOR', 'CORNER')):
        mesh.color_attributes.new(attr, data_type, domain)
    names = [a.name for a in mesh.color_attributes]
    mesh.color_attributes.render_color_index = names.index(render)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    bpy.context.scene.collection.objects.link(obj)
    obj.select_set(True)
    return obj


def color_names(obj: bpy.types.Object) -> list:
    return sorted(a.name for a in obj.data.color_attributes)


class RemoveColorAttributesTest(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()
        self.obj = mesh_with_colors("A")

    def test_every_domain_and_type_is_removed(self):
        removed, kept = colors.remove_color_attributes(self.obj.data, keep_render=False)
        self.assertEqual(sorted(removed), ["Corner Byte", "Corner Float", "Point Byte", "Point Float"])
        self.assertEqual(kept, [])
        self.assertEqual(color_names(self.obj), [])

    def test_keep_render_keeps_the_camera_icon_one(self):
        self.assertEqual(self.obj.data.color_attributes.default_color_name, "Corner Float")
        removed, kept = colors.remove_color_attributes(self.obj.data, keep_render=True)
        self.assertEqual(kept, ["Corner Float"])
        self.assertEqual(color_names(self.obj), ["Corner Float"])
        self.assertEqual(self.obj.data.color_attributes.default_color_name, "Corner Float")

    def test_a_mesh_without_colors(self):
        mesh = bpy.data.meshes.new("Plain")
        self.assertEqual(colors.remove_color_attributes(mesh, keep_render=True), ([], []))


class RemoveVertexColorsCommandTest(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()
        enable(self)
        self.options = prefs.get(bpy.context)
        self.first = mesh_with_colors("First")
        self.second = mesh_with_colors("Second", location=(2.0, 0.0, 0.0), render="Point Byte")
        self.other = mesh_with_colors("Other", location=(4.0, 0.0, 0.0))
        self.other.select_set(False)
        bpy.context.view_layer.objects.active = self.first

    def test_selected_meshes_are_cleaned_and_others_untouched(self):
        self.options.color_meshes = 'SELECTED'
        self.assertEqual(bpy.ops.flver_prep.remove_vertex_colors(), {'FINISHED'})
        self.assertEqual(color_names(self.first), [])
        self.assertEqual(color_names(self.second), [])
        self.assertEqual(len(color_names(self.other)), 4)

    def test_active_mesh_only(self):
        self.options.color_meshes = 'ACTIVE'
        bpy.ops.flver_prep.remove_vertex_colors()
        self.assertEqual(color_names(self.first), [])
        self.assertEqual(len(color_names(self.second)), 4)

    def test_keep_render_color_on_each_mesh(self):
        self.options.keep_render_color = True
        bpy.ops.flver_prep.remove_vertex_colors()
        self.assertEqual(color_names(self.first), ["Corner Float"])
        self.assertEqual(color_names(self.second), ["Point Byte"])

    def test_nothing_to_remove_cancels(self):
        bpy.ops.flver_prep.remove_vertex_colors()
        self.assertEqual(bpy.ops.flver_prep.remove_vertex_colors(), {'CANCELLED'})

    def test_unavailable_without_a_mesh_in_scope(self):
        for obj in (self.first, self.second):
            obj.select_set(False)
        self.assertFalse(bpy.ops.flver_prep.remove_vertex_colors.poll())

    def test_unavailable_in_edit_mode(self):
        bpy.ops.object.mode_set(mode='EDIT')
        try:
            self.assertFalse(bpy.ops.flver_prep.remove_vertex_colors.poll())
        finally:
            bpy.ops.object.mode_set(mode='OBJECT')


if __name__ == '__main__':
    unittest.main()
