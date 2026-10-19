# Sidebar panel: the selected armature, the two options, the commands and the
# Y-up view buttons

import bpy

from . import messages, prefs


class FS_FBX_TOOLS_PT_main(bpy.types.Panel):
    """Prepare Copy options and button in the 3D Viewport sidebar"""
    bl_label = "FS FBX Tools"
    bl_idname = "FS_FBX_TOOLS_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FS FBX"

    def draw(self, context):
        layout = self.layout
        armature_obj = context.active_object

        box = layout.box()
        if armature_obj is None or armature_obj.type != 'ARMATURE':
            box.alert = True
            box.label(text=messages.NO_ARMATURE, icon='ERROR')
        else:
            # Formatted text: translate the template, then fill it in
            text = bpy.app.translations.pgettext_iface(messages.ARMATURE)
            box.label(text=text.format(name=armature_obj.name), icon='ARMATURE_DATA',
                      translate=False)

        options = prefs.get(context)
        if options is not None:
            col = layout.column(align=True)
            col.prop(options, "mirror_z")
            col.prop(options, "flip_faces")

        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator("fs_fbx_tools.prepare_copy", icon='DUPLICATE')
        col.operator("fs_fbx_tools.prepare_export", text="Prepare and Export...", icon='EXPORT')
        col.operator("fs_fbx_tools.export_copy", text="Export Copy...", icon='EXPORT')

        # Fixed views of the Y-up copies; the axis is the side the viewer is on
        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator("fs_fbx_tools.y_up_view", text="Front (-Z, Y-Up)", icon='VIEW_ORTHO').side = 'FRONT'
        col.operator("fs_fbx_tools.y_up_view", text="Side (-X, Y-Up)", icon='VIEW_ORTHO').side = 'SIDE'
        col.operator("fs_fbx_tools.y_up_view", text="Top (+Y, Y-Up)", icon='VIEW_ORTHO').side = 'TOP'
