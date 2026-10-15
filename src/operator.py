# The Prepare Copy, Prepare and Export, Export Copy and Y-Up View commands;
# the work is in prepare.py, export.py and view.py

from typing import Optional

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy_extras.io_utils import ExportHelper

from . import export, messages, prefs, prepare, view


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


def _active_armature(operator: bpy.types.Operator,
                     context: bpy.types.Context) -> Optional[bpy.types.Object]:
    """
    Check that an armature is active and Blender is in Object mode.

    Parameters
    ----------
    operator : bpy.types.Operator
        The running command, which reports the refusal.
    context : bpy.types.Context
        Current Blender context.

    Returns
    -------
    bpy.types.Object or None
        The active armature, or None after reporting why not.
    """
    armature_obj = context.active_object
    if armature_obj is None or armature_obj.type != 'ARMATURE':
        operator.report({'ERROR'}, _text(messages.SELECT_ARMATURE))
        return None
    if context.mode != 'OBJECT':
        operator.report({'ERROR'}, _text(messages.OBJECT_MODE))
        return None
    return armature_obj


def _prepare(operator: bpy.types.Operator, context: bpy.types.Context,
             armature_obj: bpy.types.Object) -> Optional[prepare.PreparedCopy]:
    """
    Run Prepare Copy with the panel options.

    Parameters
    ----------
    operator : bpy.types.Operator
        The running command, which reports the refusal.
    context : bpy.types.Context
        Current Blender context.
    armature_obj : bpy.types.Object
        The armature to copy.

    Returns
    -------
    prepare.PreparedCopy or None
        What was made, or None after reporting that the armature has no meshes.
    """
    if not prepare.armature_meshes(armature_obj, context.scene.objects):
        operator.report({'ERROR'}, _text(messages.NO_MESHES, name=armature_obj.name))
        return None
    options = prefs.get(context)
    mirror_z = bool(options and options.mirror_z)
    flip_faces = bool(options and options.flip_faces)
    return prepare.prepare_copy(context, armature_obj, mirror_z, flip_faces)


def _export(operator: bpy.types.Operator, context: bpy.types.Context,
            collection: bpy.types.Collection, filepath: str) -> set:
    """
    Export a prepared collection and report the result.

    Parameters
    ----------
    operator : bpy.types.Operator
        The running command, which reports the result.
    context : bpy.types.Context
        Current Blender context.
    collection : bpy.types.Collection
        A collection made by Prepare Copy.
    filepath : str
        Path of the FBX file to write.

    Returns
    -------
    set
        ``{'FINISHED'}``, or ``{'CANCELLED'}`` when the export failed.
    """
    try:
        count = export.export_collection(context, collection, filepath)
    except RuntimeError as error:
        operator.report({'ERROR'}, _text(messages.EXPORT_FAILED, error=error))
        return {'CANCELLED'}
    mirrored = bool(collection.get(prepare.MIRROR_Z_KEY, False))
    template = messages.EXPORTED_MIRRORED if mirrored else messages.EXPORTED_PLAIN
    operator.report({'INFO'}, _text(template, count=count, collection=collection.name,
                                    path=filepath))
    return {'FINISHED'}


class FS_FBX_TOOLS_OT_prepare_copy(bpy.types.Operator):
    """Copy the active armature and its meshes into a new collection, in the axes FbxImporter reads"""
    bl_idname = "fs_fbx_tools.prepare_copy"
    bl_label = "Prepare Copy"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armature_obj = _active_armature(self, context)
        if armature_obj is None:
            return {'CANCELLED'}
        result = _prepare(self, context, armature_obj)
        if result is None:
            return {'CANCELLED'}
        mirrored = bool(result.collection[prepare.MIRROR_Z_KEY])
        template = messages.PREPARED_MIRRORED if mirrored else messages.PREPARED_PLAIN
        self.report({'INFO'}, _text(template, count=len(result.meshes),
                                    collection=result.collection.name))
        return {'FINISHED'}


class FS_FBX_TOOLS_OT_prepare_export(bpy.types.Operator, ExportHelper):
    """Prepare a copy, then export it as FBX for FbxImporter"""
    bl_idname = "fs_fbx_tools.prepare_export"
    bl_label = "Prepare and Export"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    def execute(self, context):
        armature_obj = _active_armature(self, context)
        if armature_obj is None:
            return {'CANCELLED'}
        result = _prepare(self, context, armature_obj)
        if result is None:
            return {'CANCELLED'}
        return _export(self, context, result.collection, self.filepath)


class FS_FBX_TOOLS_OT_export_copy(bpy.types.Operator, ExportHelper):
    """Export the prepared copy as FBX for FbxImporter"""
    bl_idname = "fs_fbx_tools.export_copy"
    bl_label = "Export Copy"
    bl_options = {'REGISTER'}

    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    def execute(self, context):
        armature_obj = _active_armature(self, context)
        if armature_obj is None:
            return {'CANCELLED'}
        collection = export.prepared_collection(armature_obj)
        if collection is None:
            self.report({'ERROR'}, _text(messages.RUN_PREPARE_FIRST))
            return {'CANCELLED'}
        return _export(self, context, collection, self.filepath)


class FS_FBX_TOOLS_OT_y_up_view(bpy.types.Operator):
    """Turn the 3D Viewport to a fixed orthographic view of the Y-up copies"""
    bl_idname = "fs_fbx_tools.y_up_view"
    bl_label = "Y-Up View"
    # A view change, not undoable, like Blender's own view commands
    bl_options = {'REGISTER'}

    side: EnumProperty(
        name="Side",
        items=(
            ('FRONT', "Front", "Look from the -Z side towards +Z, with +Y up"),
            ('SIDE', "Side", "Look from the -X side towards +X, with +Y up"),
            ('TOP', "Top", "Look from the +Y side down towards -Y, with +Z up the screen"),
        ),
        default='FRONT',
    )

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space is not None and space.type == 'VIEW_3D'

    def execute(self, context):
        region_3d = context.space_data.region_3d
        region_3d.view_rotation = view.view_rotation(self.side)
        region_3d.view_perspective = 'ORTHO'
        return {'FINISHED'}

