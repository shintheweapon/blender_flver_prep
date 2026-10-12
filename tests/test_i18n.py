# Tests for the Simplified Chinese table and its registration

import string
import unittest

import bpy

import helpers
from src import i18n_zh_hans, messages, operator, prefs
from test_operator import enable


def fields(text):
    """The named fields of a format string, sorted."""
    return sorted(name for _, name, _, _ in string.Formatter().parse(text) if name)


class TableTests(unittest.TestCase):

    def setUp(self):
        self.table = i18n_zh_hans.table()

    def test_every_interface_text_has_an_entry(self):
        command = operator.FS_FBX_TOOLS_OT_prepare_copy
        options = prefs.FS_FBX_TOOLS_preferences.__annotations__
        texts = [command.bl_label, command.__doc__]
        for name in ('mirror_z', 'flip_faces'):
            keywords = options[name].keywords
            texts += [keywords['name'], keywords['description']]
        texts += list(messages.templates().values())
        missing = [t for t in texts if (i18n_zh_hans.DEFAULT, t) not in self.table]
        self.assertEqual(missing, [])

    def test_label_in_the_operator_context_too(self):
        self.assertEqual(self.table[(i18n_zh_hans.OPERATOR, "Prepare Copy")], "准备副本")

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

    def test_label_tooltip_options_and_reports_in_chinese(self):
        tr = bpy.app.translations
        self.assertEqual(tr.pgettext_iface("Prepare Copy", "Operator"), "准备副本")
        self.assertEqual(tr.pgettext_tip(operator.FS_FBX_TOOLS_OT_prepare_copy.__doc__),
                         "把当前骨架及其网格复制到新集合，并转换为 FbxImporter 读取的坐标轴")
        self.assertEqual(tr.pgettext_iface("Mirror Z"), "镜像 Z")
        self.assertEqual(tr.pgettext_iface("Flip Faces"), "翻转面")
        self.assertEqual(tr.pgettext_rpt(messages.PREPARED_PLAIN).format(count=2, collection="A_fs"),
                         "已在集合 A_fs 中准备 2 个网格。请在 FbxImporter 中勾选 Mirror Z")
        self.assertEqual(tr.pgettext_rpt(messages.NO_MESHES).format(name="A"), "A 没有网格")


if __name__ == '__main__':
    unittest.main()
