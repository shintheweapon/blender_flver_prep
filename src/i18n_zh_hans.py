# Simplified Chinese (zh_HANS) translations of the add-on's texts; plain Python.
# Keys are (context, English text) as bpy.app.translations expects; the
# English texts must match the code exactly (tests check this). The words
# follow Blender's own zh_HANS translation: 骨架, 网格, 集合, 物体模式, 镜像,
# 翻转, 面, 法向. "Mirror Z" and "Flip Faces" stay English where they name
# FbxImporter's own options.

from typing import Dict, Tuple

from . import messages

# Contexts used by Blender: '*' for most texts, 'Operator' for operator labels
# and button texts
DEFAULT = '*'
OPERATOR = 'Operator'

# Command labels and the panel's button texts: Blender looks these up in the
# operator context (buttons, F3 search)
LABELS = {
    "Prepare Copy": "准备副本",
    "Prepare and Export": "准备并导出",
    "Export Copy": "导出副本",
    "Y-Up View": "Y 向上视图",
    # Panel button texts (the dots mean a file dialog follows)
    "Prepare and Export...": "准备并导出...",
    "Export Copy...": "导出副本...",
    "Remove Vertex Colors": "移除顶点色",
    "Roll View": "滚动视图",
    # Y-Up View buttons: Blender's view names (后, 左, 右, 顶, 底 with 视图),
    # 正面 and 背面 for the character's face and back, and Blender's 逆时针
    # and 顺时针 for the rolls
    "Face (-Z)": "正面 (-Z)",
    "Face (+Z)": "正面 (+Z)",
    "Back (-Z)": "背面 (-Z)",
    "Back (+Z)": "背面 (+Z)",
    "Left (-X)": "左视图 (-X)",
    "Right (+X)": "右视图 (+X)",
    "Top (+Y)": "顶视图 (+Y)",
    "Bottom (-Y)": "底视图 (-Y)",
    "Anti-clockwise": "逆时针",
    "Clockwise": "顺时针",
}

_TEXTS = {
    **LABELS,
    "Turn the 3D Viewport to a fixed orthographic view of the Y-up copies":
        "把 3D 视图转到 Y 向上副本的固定正交视图",
    "Look from the -Z side towards +Z, with +Y up":
        "从 -Z 一侧看向 +Z，+Y 向上",
    "Look from the +Z side towards -Z, with +Y up":
        "从 +Z 一侧看向 -Z，+Y 向上",
    "Look from the -X side towards +X, with +Y up (Side Up: Y-Up) or -Z up (Side Up: Z-Down)":
        "从 -X 一侧看向 +X，+Y 向上（侧视图朝上：Y 向上）或 -Z 向上（侧视图朝上：Z 向下）",
    "Look from the +X side towards -X, with +Y up (Side Up: Y-Up) or -Z up (Side Up: Z-Down)":
        "从 +X 一侧看向 -X，+Y 向上（侧视图朝上：Y 向上）或 -Z 向上（侧视图朝上：Z 向下）",
    "Look from the +Y side down towards -Y, with +Z up the screen":
        "从 +Y 一侧向下看向 -Y，屏幕上方为 +Z",
    "Look from the -Y side up towards +Y, with -Z up the screen":
        "从 -Y 一侧向上看向 +Y，屏幕上方为 -Z",
    "Y-Up Views": "Y 向上视图",
    "Turn the 3D Viewport's picture 90 degrees": "把 3D 视图的画面旋转 90 度",
    "Turn the picture 90 degrees anti-clockwise": "把画面逆时针旋转 90 度",
    "Turn the picture 90 degrees clockwise": "把画面顺时针旋转 90 度",
    "Side Up": "侧视图朝上",
    "Which axis the Left and Right views put up the screen": "左视图和右视图中朝向屏幕上方的轴",
    "Y-Up": "Y 向上",
    "Z-Down": "Z 向下",
    "Left and Right show +Y up the screen": "左视图和右视图中 +Y 朝向屏幕上方",
    "Left and Right show -Z up the screen, so +Z points down":
        "左视图和右视图中 -Z 朝向屏幕上方，+Z 朝下",
    "Prepare a copy, then export it as FBX for FbxImporter":
        "准备副本，然后导出为供 FbxImporter 使用的 FBX",
    "Export the prepared copy as FBX for FbxImporter":
        "把已准备的副本导出为供 FbxImporter 使用的 FBX",
    "Copy the active armature and its meshes into a new collection, in the axes FbxImporter reads":
        "把当前骨架及其网格复制到新集合，并转换为 FbxImporter 读取的坐标轴",
    "Mirror Z": "镜像 Z",
    "Negate Z of positions and normals, as FbxImporter's Mirror Z does":
        "对位置和法向的 Z 取反，与 FbxImporter 的 Mirror Z 相同",
    "Flip Faces": "翻转面",
    "Reverse the order of each face's corners, as FbxImporter's Flip Faces does":
        "反转每个面的顶点顺序，与 FbxImporter 的 Flip Faces 相同",
    messages.ARMATURE: "骨架：{name}",
    messages.NO_ARMATURE: "未选择骨架",
    messages.SELECT_ARMATURE: "请先选择一个骨架",
    messages.NO_MESHES: "{name} 没有网格",
    messages.OBJECT_MODE: "请先切换到物体模式",
    messages.PREPARED_MIRRORED:
        "已在集合 {collection} 中准备 {count} 个网格。已应用镜像 Z：在 FbxImporter 中不要勾选 Mirror Z",
    messages.PREPARED_PLAIN:
        "已在集合 {collection} 中准备 {count} 个网格。请在 FbxImporter 中勾选 Mirror Z",
    messages.RUN_PREPARE_FIRST: "请先运行“准备副本”",
    messages.EXPORT_FAILED: "导出失败：{error}",
    messages.EXPORTED_MIRRORED:
        "已将集合 {collection} 中的 {count} 个网格导出到 {path}。已应用镜像 Z：在 FbxImporter 中不要勾选 Mirror Z",
    "Remove every Color Attribute (vertex color) from the meshes, in Object Mode":
        "在物体模式下移除网格的所有颜色属性（顶点色）",
    "Meshes": "网格",
    "Which meshes Remove Vertex Colors works on": "“移除顶点色”作用于哪些网格",
    "Selected Meshes": "所选网格",
    "Every selected mesh": "所有选中的网格",
    "Active Mesh": "活动网格",
    "Only the active mesh": "仅活动网格",
    "Keep Render Color": "保留渲染颜色",
    "Remove Vertex Colors keeps the render color, the one marked with the camera icon in the "
    "Color Attributes list":
        "“移除顶点色”保留渲染颜色，即颜色属性列表中带相机图标的那一项",
    messages.REMOVED_COLORS: "已从 {meshes} 个网格移除 {count} 个颜色属性",
    messages.REMOVED_COLORS_KEPT: "已从 {meshes} 个网格移除 {count} 个颜色属性。已在 {kept} 个网格上保留渲染颜色",
    messages.NO_COLORS: "没有可移除的颜色属性",
    messages.EXPORTED_PLAIN:
        "已将集合 {collection} 中的 {count} 个网格导出到 {path}。请在 FbxImporter 中勾选 Mirror Z",
}


def table() -> Dict[Tuple[str, str], str]:
    """
    Build the translation table to register with Blender.

    Returns
    -------
    dict
        ``{(context, English): Chinese}``. Every text is under the default
        context; the command labels and the panel's button texts are also
        under the operator context, where Blender looks them up for buttons
        and F3 search.
    """
    entries = {(DEFAULT, english): chinese for english, chinese in _TEXTS.items()}
    entries.update({(OPERATOR, english): chinese for english, chinese in LABELS.items()})
    return entries
