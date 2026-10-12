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
    # Panel button texts (the dots mean a file dialog follows)
    "Prepare and Export...": "准备并导出...",
    "Export Copy...": "导出副本...",
}

_TEXTS = {
    **LABELS,
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
