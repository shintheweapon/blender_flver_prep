# FS FBX Tools: prepares Blender models for The12thAvenger's FbxImporter

import bpy

from . import i18n_zh_hans, operator, panel, prefs

classes = (
    prefs.FS_FBX_TOOLS_preferences,
    operator.FS_FBX_TOOLS_OT_prepare_copy,
    panel.FS_FBX_TOOLS_PT_main,
)


def register():
    """Register the translations, preferences, command and sidebar panel."""
    bpy.app.translations.register(__name__, {'zh_HANS': i18n_zh_hans.table()})
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister everything added by :func:`register`."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.app.translations.unregister(__name__)
