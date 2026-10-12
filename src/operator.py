# The Prepare Copy command; the conversion itself is in prepare.py

import bpy

from . import messages, prefs, prepare


def _text(template: str, **fields) -> str:
    """
    Fill a message template from :mod:`messages`, in the interface language
    when Blender translates reports.

    Parameters
    ----------
    template : str
        One of the templates in :mod:`messages`.
    **fields
        Values for its named fields.

    Returns
    -------
    str
        The message.
    """
    return bpy.app.translations.pgettext_rpt(template).format(**fields)


class FS_FBX_TOOLS_OT_prepare_copy(bpy.types.Operator):
    """Copy the active armature and its meshes into a new collection, in the axes FbxImporter reads"""
    bl_idname = "fs_fbx_tools.prepare_copy"
    bl_label = "Prepare Copy"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armature_obj = context.active_object
        if armature_obj is None or armature_obj.type != 'ARMATURE':
            self.report({'ERROR'}, _text(messages.SELECT_ARMATURE))
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            self.report({'ERROR'}, _text(messages.OBJECT_MODE))
            return {'CANCELLED'}
        if not prepare.armature_meshes(armature_obj, context.scene.objects):
            self.report({'ERROR'}, _text(messages.NO_MESHES, name=armature_obj.name))
            return {'CANCELLED'}
        options = prefs.get(context)
        mirror_z = bool(options and options.mirror_z)
        flip_faces = bool(options and options.flip_faces)
        result = prepare.prepare_copy(context, armature_obj, mirror_z, flip_faces)
        template = messages.PREPARED_MIRRORED if mirror_z else messages.PREPARED_PLAIN
        self.report({'INFO'}, _text(template, count=len(result.meshes),
                                    collection=result.collection.name))
        return {'FINISHED'}
