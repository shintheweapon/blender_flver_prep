# Tests for the Simplified Chinese table and its registration

import string
import unittest

import bpy

import helpers
from src import i18n_zh_hans, messages, operator, prefs
from test_operator import enable

COMMANDS = (operator.FLVER_PREP_OT_prepare_copy, operator.FLVER_PREP_OT_prepare_export,
            operator.FLVER_PREP_OT_export_copy, operator.FLVER_PREP_OT_y_up_view,
            operator.FLVER_PREP_OT_roll_view, operator.FLVER_PREP_OT_remove_vertex_colors)
# Panel buttons with their own text: (command, English, Chinese)
BUTTONS = ((operator.FLVER_PREP_OT_prepare_export, "Prepare and Export...", "准备并导出..."),
           (operator.FLVER_PREP_OT_export_copy, "Export Copy...", "导出副本..."),
           (operator.FLVER_PREP_OT_y_up_view, "Face (-Z)", "正面 (-Z)"),
           (operator.FLVER_PREP_OT_y_up_view, "Face (+Z)", "正面 (+Z)"),
           (operator.FLVER_PREP_OT_y_up_view, "Back (-Z)", "背面 (-Z)"),
           (operator.FLVER_PREP_OT_y_up_view, "Back (+Z)", "背面 (+Z)"),
           (operator.FLVER_PREP_OT_y_up_view, "Left (-X)", "左视图 (-X)"),
           (operator.FLVER_PREP_OT_y_up_view, "Right (+X)", "右视图 (+X)"),
           (operator.FLVER_PREP_OT_y_up_view, "Top (+Y)", "顶视图 (+Y)"),
           (operator.FLVER_PREP_OT_y_up_view, "Bottom (-Y)", "底视图 (-Y)"),
           (operator.FLVER_PREP_OT_roll_view, "Anti-clockwise", "逆时针"),
           (operator.FLVER_PREP_OT_roll_view, "Clockwise", "顺时针"))


def fields(text):
    """The named fields of a format string, sorted."""
    return sorted(name for _, name, _, _ in string.Formatter().parse(text) if name)


class TableTests(unittest.TestCase):

    def setUp(self):
        self.table = i18n_zh_hans.table()

    def test_every_interface_text_has_an_entry(self):
        options = prefs.FLVER_PREP_preferences.__annotations__
        texts = [english for _, english, _ in BUTTONS]
        for command in COMMANDS:
            texts += [command.bl_label, command.__doc__]
        for name in ('mirror_z', 'flip_faces', 'color_meshes', 'keep_render_color', 'side_up'):
            keywords = options[name].keywords
            texts += [keywords['name'], keywords['description']]
        # Choices of Meshes and Side Up, with their tooltips
        for name in ('color_meshes', 'side_up'):
            for _, item_name, description in options[name].keywords['items']:
                texts += [item_name, description]
        # Tooltips of the Y-Up View sides and the Roll View directions
        sides = operator.FLVER_PREP_OT_y_up_view.__annotations__['side'].keywords['items']
        texts += [description for _, _, description in sides]
        directions = operator.FLVER_PREP_OT_roll_view.__annotations__['direction'].keywords['items']
        texts += [description for _, _, description in directions]
        texts.append("Y-Up Views")
        texts += list(messages.templates().values())
        missing = [t for t in texts if (i18n_zh_hans.DEFAULT, t) not in self.table]
        self.assertEqual(missing, [])

    def test_labels_in_the_operator_context_too(self):
        for command in COMMANDS:
            self.assertEqual(self.table[(i18n_zh_hans.OPERATOR, command.bl_label)],
                             self.table[(i18n_zh_hans.DEFAULT, command.bl_label)])
        # The panel's own button texts are looked up there as well
        for _, english, chinese in BUTTONS:
            self.assertEqual(self.table[(i18n_zh_hans.OPERATOR, english)], chinese)

    def test_translations_keep_the_same_fields(self):
        for (_, english), chinese in self.table.items():
            self.assertEqual(fields(english), fields(chinese), english)

    def test_no_entry_is_empty_or_untranslated(self):
        for (_, english), chinese in self.table.items():
            self.assertTrue(chinese.strip(), english)
            self.assertNotEqual(chinese, english)


class ChineseInterfaceTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()
        enable(self)
        view = bpy.context.preferences.view
        self.saved = (view.language, view.use_translate_interface,
                      view.use_translate_tooltips, view.use_translate_reports)
        view.language = 'zh_HANS'
        view.use_translate_interface = True
        view.use_translate_tooltips = True
        view.use_translate_reports = True

    def tearDown(self):
        view = bpy.context.preferences.view
        (view.language, view.use_translate_interface,
         view.use_translate_tooltips, view.use_translate_reports) = self.saved

    def test_command_tooltips_in_their_own_context(self):
        # Blender looks a command's tooltip up in the command's translation
        # context ("Operator"), not the default one
        tr = bpy.app.translations
        for command in COMMANDS:
            # The registered command's RNA holds the tooltip as Blender shows it
            rna = getattr(bpy.ops.flver_prep, command.bl_idname.split('.')[1]).get_rna_type()
            self.assertTrue(rna.description)
            with self.subTest(command=command.bl_idname):
                self.assertNotEqual(
                    tr.pgettext_tip(rna.description, rna.translation_context), rna.description)

    def test_label_tooltip_options_and_reports_in_chinese(self):
        tr = bpy.app.translations
        self.assertEqual(tr.pgettext_iface("Prepare Copy", "Operator"), "准备副本")
        self.assertEqual(tr.pgettext_tip(operator.FLVER_PREP_OT_prepare_copy.__doc__),
                         "把当前骨架及其网格复制到新集合，并转换为 FbxImporter 读取的坐标轴")
        self.assertEqual(tr.pgettext_iface("Mirror Z"), "镜像 Z")
        self.assertEqual(tr.pgettext_iface("Flip Faces"), "翻转面")
        self.assertEqual(tr.pgettext_rpt(messages.PREPARED_PLAIN).format(count=2, collection="A_fs"),
                         "已在集合 A_fs 中准备 2 个网格。请在 FbxImporter 中勾选 Mirror Z")
        self.assertEqual(tr.pgettext_rpt(messages.NO_MESHES).format(name="A"), "A 没有网格")
        self.assertEqual(tr.pgettext_iface("Export Copy", "Operator"), "导出副本")
        # A text= on layout.operator is translated in the command's context
        for command, english, chinese in BUTTONS:
            self.assertEqual(tr.pgettext_iface(english, command.bl_rna.translation_context), chinese)
        self.assertEqual(tr.pgettext_rpt(messages.EXPORTED_MIRRORED).format(
            count=2, collection="A_fs", path="p.fbx"),
            "已将集合 A_fs 中的 2 个网格导出到 p.fbx。已应用镜像 Z：在 FbxImporter 中不要勾选 Mirror Z")
        self.assertEqual(tr.pgettext_rpt(messages.RUN_PREPARE_FIRST), "请先运行“准备副本”")
        self.assertEqual(tr.pgettext_iface("Remove Vertex Colors", "Operator"), "移除顶点色")
        self.assertEqual(tr.pgettext_iface("Keep Render Color"), "保留渲染颜色")
        self.assertEqual(tr.pgettext_rpt(messages.REMOVED_COLORS).format(count=3, meshes=2),
                         "已从 2 个网格移除 3 个颜色属性")


if __name__ == '__main__':
    unittest.main()
