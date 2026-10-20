# Sidebar panel: the selected armature, the two options, the commands, the
# Y-up view buttons and Remove Vertex Colors

import bpy

from . import messages, operator, prefs, view

# Texts of the first view row, for the side the copy's face is on and the
# opposite side; fixed strings so that they can be translated
FACE_LABELS = {'NEG_Z': "Face (-Z)", 'POS_Z': "Face (+Z)"}
BACK_LABELS = {'NEG_Z': "Back (-Z)", 'POS_Z': "Back (+Z)"}


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
        col.label(text="Y-Up Views")
        if options is not None:
            row = col.row()
            row.label(text="Side Up")
            row.row(align=True).prop(options, "side_up", expand=True)
        face = view.face_side(operator.mirrored_for(context))
        back = 'POS_Z' if face == 'NEG_Z' else 'NEG_Z'
        rows = ((face, FACE_LABELS[face], back, BACK_LABELS[back]),
                ('NEG_X', "Left (-X)", 'POS_X', "Right (+X)"),
                ('POS_Y', "Top (+Y)", 'NEG_Y', "Bottom (-Y)"))
        col = layout.column(align=True)
        col.scale_y = 1.5
        for left_side, left_text, right_side, right_text in rows:
            row = col.row(align=True)
            row.operator("fs_fbx_tools.y_up_view", text=left_text, icon='VIEW_ORTHO').side = left_side
            row.operator("fs_fbx_tools.y_up_view", text=right_text, icon='VIEW_ORTHO').side = right_side
        row = col.row(align=True)
        row.operator("fs_fbx_tools.roll_view", text="Roll Left", icon='LOOP_BACK').direction = 'LEFT'
        row.operator("fs_fbx_tools.roll_view", text="Roll Right", icon='LOOP_FORWARDS').direction = 'RIGHT'

        # Remove Vertex Colors and its two options
        col = layout.column(align=True)
        if options is not None:
            col.row(align=True).prop(options, "color_meshes", expand=True)
            col.prop(options, "keep_render_color")
        col.operator("fs_fbx_tools.remove_vertex_colors", icon='GROUP_VCOL')
