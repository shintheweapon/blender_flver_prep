"""
The paper's figures in Simplified Chinese: a catalogue of every English string
in them and its Chinese form, applied to the generated SVGs.

``build`` turns the paper's figures into ``<name>.zh.svg`` files; the figure
code and the English SVGs are not touched. Only the character data of
``<text>``, ``<title>`` and ``<desc>`` changes, so animations inside a text
element keep working. Terms follow ``docs/paper/glossary.zh-CN.md``.
"""

import html
import re

# The paper's figures, in the order the paper shows them
PAPER_FIGURES = ("paper_normal_map_layout.svg", "tangent_frame.svg", "paper_axis_swap_animated.svg",
                 "paper_axis_swap.svg", "paper_layout_test.svg", "paper_tangent_directions.svg",
                 "paper_dome_tilts.svg", "paper_uv_triangle.svg", "paper_channel_changes.svg",
                 "paper_ways_out_of_blender.svg")

# Chinese fonts after the figures' own, so every viewer draws the Chinese text in a sans-serif face
FONT_STACK = 'Helvetica,Arial,sans-serif'
ZH_FONT_STACK = 'Helvetica,Arial,"Microsoft YaHei","PingFang SC","Noto Sans CJK SC","Source Han Sans SC",sans-serif'

ZH = {
    # Fig. 1, the layout of a normal map
    "The layout of a normal map": "法线贴图的布局",
    ("A texture with U running right and V running down from row 0 at the top. Red stores the tangent-space normal's x "
     "component (towards +U), green its y component (towards +V). Blue is held to store gloss and alpha other data; "
     "this was not tested. On a raised bump, red is high on its +U side and green on its +V side."):
        ("一张纹理，U 向右，V 从顶部的第 0 行向下。红色通道存储切线空间法线的 x 分量（朝 +U），绿色通道存储其 y 分量"
         "（朝 +V）。一般认为蓝色通道存储光泽度、Alpha 通道存储其他数据；这一点未经测试。在凸起处，红色通道的值在其 +U 一侧偏高，"
         "绿色通道的值在其 +V 一侧偏高。"),
    "(0, 0), row 0": "(0, 0)，第 0 行",
    "bump": "凸起",
    "Red: x component, towards +U": "红色通道：x 分量，朝 +U",
    "Green: y component, towards +V": "绿色通道：y 分量，朝 +V",
    "V runs down the image (DirectX layout)": "V 沿图像向下（DirectX 布局）",
    "Blue: gloss. Alpha: other data": "蓝色通道：光泽度。Alpha 通道：其他数据",
    "As held by modders; not tested here": "模组社区的看法；本文未测试",
    "On a raised bump, red is high on its +U side": "在凸起处，红色通道的值在其 +U 一侧偏高，",
    "and green is high on its +V side": "绿色通道的值在其 +V 一侧偏高",
    # Fig. 2, the tangent frame
    "The tangent frame on the game's own models": "游戏原生模型的切线坐标系",
    ("Two UV islands lying flat, as seen in game, with N pointing up and T along +V towards the viewer. In FLVER's "
     "left-handed space N x T follows the left-hand rule and points left. On the unmirrored island +U runs right, so "
     "W = -1 turns N x T to point along +U. On the mirrored island +U runs left, N x T already points along +U, and "
     "W = +1."):
        ("两个平放的 UV 岛，按游戏内所见，N 朝上，T 沿 +V 朝向观察者。在 FLVER 的左手坐标系中，N × T 遵循左手定则，"
         "指向左方。在非镜像岛上，+U 向右，因此 W = -1 使 N × T 指向 +U。在镜像岛上，+U 向左，N × T 已指向 +U，"
         "W = +1。"),
    "row 0": "第 0 行",
    "Unmirrored island, W = −1": "非镜像岛，W = −1",
    "Mirrored island, W = +1": "镜像岛，W = +1",
    "T, along +V": "T，沿 +V",
    "W(N × T), along +U": "W(N × T)，沿 +U",
    "N × T (left-hand rule)": "N × T（左手定则）",
    # Fig. 3(a), the axis swap, animated
    "The axis swap from Blender into FLVER space, animated": "从 Blender 到 FLVER 空间的坐标轴交换（动画）",
    ("Animated over 30 seconds: fixed axes drawn as Blender's Front view shows them, +X to the right, +Z up and +Y "
     "into the scene. A character stands facing the viewer, up +Z, forward -Y, left side +X, with labels up, forward "
     "and left that move with it. Its coordinates are rotated -90 degrees about X, which lays it on its back, up +Y "
     "and forward +Z; then Z is negated, a reflection, which turns it face down, forward -Z, with the left side still "
     "at +X. A text names each step, and a legend gives the colours: gray body, amber forward (nose), purple left arm "
     "and hand, and the three axes."):
        ("30 秒的动画：固定坐标轴按 Blender 前视图的方向绘制，+X 向右，+Z 向上，+Y 指向画面内。一个角色面向观察者"
         "站立，上方 +Z，前方 -Y，左侧 +X，标签“上”“前”“左”随角色移动。其坐标绕 X 轴旋转 -90 度，使角色仰卧，"
         "上方 +Y，前方 +Z；随后 Z 取反（一次反射），使角色俯卧，前方 -Z，左侧仍为 +X。文字标出每一步，图例给出"
         "颜色：灰色为身体，琥珀色为前方（鼻子），紫色为左臂和左手，以及三条坐标轴。"),
    "up": "上",
    "forward": "前",
    "left": "左",
    "1. Blender": "1. Blender",
    "Up +Z, forward −Y, left side +X.": "上 +Z，前 −Y，左侧 +X。",
    "Right-handed.": "右手坐标系。",
    "2. Rotate −90° about X": "2. 绕 X 轴旋转 −90°",
    "Up turns to +Y, forward to +Z.": "上转为 +Y，前转为 +Z。",
    "3. After the rotation": "3. 旋转之后",
    "Up +Y, forward +Z, left side +X.": "上 +Y，前 +Z，左侧 +X。",
    "Still right-handed.": "仍为右手坐标系。",
    "4. Negate Z": "4. Z 取反",
    "Forward flips to −Z: a reflection,": "前方翻转为 −Z：这是反射，",
    "not a rotation.": "而非旋转。",
    "5. FLVER": "5. FLVER",
    "Up +Y, forward −Z, left side +X.": "上 +Y，前 −Z，左侧 +X。",
    "Body": "身体",
    "Forward (nose)": "前方（鼻子）",
    "Left arm and hand": "左臂和左手",
    # Fig. 3(b), the axis swap, static
    "The axis swap from Blender into FLVER space": "从 Blender 到 FLVER 空间的坐标轴交换",
    ("Three panels show a character's axes seen from in front, with its left side to the right of the screen. In "
     "Blender, X points right, Z up and Y into the screen: right-handed, with forward along -Y. After a -90 degree "
     "rotation about X, Y points up and Z out of the screen: still right-handed, with forward along +Z. After Z is "
     "negated, Z points into the screen: left-handed, as in FLVER, with forward along -Z and the left side still along "
     "+X."):
        ("三个面板从正面展示角色的坐标轴，其左侧位于屏幕右边。在 Blender 中，X 向右，Z 向上，Y 指向屏幕内：右手"
         "坐标系，前方沿 -Y。绕 X 轴旋转 -90 度后，Y 向上，Z 指向屏幕外：仍为右手坐标系，前方沿 +Z。Z 取反后，Z "
         "指向屏幕内：左手坐标系，与 FLVER 相同，前方沿 -Z，左侧仍沿 +X。"),
    "Blender": "Blender",
    "Right-handed": "右手坐标系",
    "Forward −Y, up +Z, left side +X": "前 −Y，上 +Z，左侧 +X",
    "Rotated −90° about X": "绕 X 轴旋转 −90°",
    "Forward +Z, up +Y, left side +X": "前 +Z，上 +Y，左侧 +X",
    "Then Z negated: FLVER": "再将 Z 取反：FLVER",
    "Left-handed": "左手坐标系",
    "Forward −Z, up +Y, left side +X": "前 −Z，上 +Y，左侧 +X",
    "Out of the screen": "指向屏幕外",
    "Into the screen": "指向屏幕内",
    "Each panel: the character seen from in front.": "每个面板：从正面看角色。",
    # Fig. 4, the layout test
    "The layout test on vanilla normal maps": "原版法线贴图的布局检验",
    ("Horizontal bars, one per file-name prefix of the game's part normal maps, each split into the share of its "
     "testable maps on which the DirectX pairing (red with U, green with V) wins with a positive correlation, with a "
     "negative one (green inverted), or the swapped pairing wins. The DirectX pairing with a positive correlation "
     "fills almost every bar. Columns give the testable maps and the untestable maps per prefix."):
        ("横条图，游戏部件法线贴图的每个文件名前缀一条，每条按可检验贴图的比例分段：DirectX 配对（红色通道对 U、绿色通道"
         "对 V）以正相关胜出、以负相关胜出（绿色通道反转），或交换配对胜出。以正相关胜出的 DirectX 配对几乎占满每一条。"
         "各列给出每个前缀的可检验贴图数和不可检验贴图数。"),
    "Share of testable maps": "可检验贴图的比例",
    "Testable maps": "可检验贴图",
    "Untestable": "不可检验",
    "WP (weapons)": "WP（武器）",
    "BD (body)": "BD（身体）",
    "HD (head)": "HD（头部）",
    "LG (legs)": "LG（腿部）",
    "AM (arms)": "AM（手臂）",
    "DirectX pairing, positive": "DirectX 配对，正相关",
    "DirectX pairing, negative (green inverted)": "DirectX 配对，负相关（绿色通道反转）",
    "Swapped pairing": "交换配对",
    # Fig. 6, the directions read
    "The directions the game reads green and red": "游戏读取绿色和红色通道的方向",
    ("Three sheets lying flat with N up, +U to the right and +V towards the viewer. Vanilla tangents: green is read "
     "along +V and red along +U. Tangents along +U, imported without a mirror: green along +U and red along -V, a 90° "
     "anticlockwise rotation. Tangents along +U, imported with Z mirrored: green along +U and red along +V, red and "
     "green swapped."):
        ("三张平放的面片，N 朝上，+U 向右，+V 朝向观察者。原版切线：绿色通道沿 +V 读取，红色通道沿 +U 读取。沿 +U 的切线，"
         "无镜像导入：绿色通道沿 +U，红色通道沿 -V，即逆时针旋转 90°。沿 +U 的切线，Z 轴镜像导入：绿色通道沿 +U，红色通道沿 +V，"
         "红色和绿色通道互换。"),
    "Vanilla tangents": "原版切线",
    "as the game's own": "即游戏原生",
    "models store them": "模型存储的切线",
    "Tangents along +U": "沿 +U 的切线",
    "imported": "导入时",
    "without a mirror": "无镜像",
    "with Z mirrored": "Z 轴镜像",
    "T: the game reads green along it": "T：游戏沿此方向读取绿色通道",
    "W(N × T): the game reads red along it": "W(N × T)：游戏沿此方向读取红色通道",
    # Fig. 7, the dome
    "The tangent-space normals the game decodes around a raised dome": "游戏在凸起圆顶周围解码出的切线空间法线",
    ("Animated. Three panels, each with the frame (green T, red W(N x T)) and the tangent-space normals the game "
     "decodes around a raised dome. Vanilla tangents: the normals point outward and the dome reads raised. Tangents "
     "along +U, imported without a mirror: the frame and every normal rotate by 90° anticlockwise, so the normals run "
     "round the dome. Tangents along +U, imported with Z mirrored: the frame and every normal are reflected about the "
     "U = V diagonal, so the normals on that diagonal stay outward (raised), those on the other diagonal turn inward "
     "(dented) and those on the U and V axes turn sideways."):
        ("动画。三个面板，各含切线坐标系（绿色 T，红色 W(N × T)）和游戏在凸起圆顶周围解码出的切线空间法线。原版"
         "切线：法线朝外，圆顶呈凸起。沿 +U 的切线，无镜像导入：坐标系和每条法线逆时针旋转 90°，法线绕圆顶环行。"
         "沿 +U 的切线，Z 轴镜像导入：坐标系和每条法线关于 U = V 对角线反射，该对角线上的法线仍朝外（凸起），"
         "另一条对角线上的法线转向内（凹陷），U 轴和 V 轴上的法线转向侧面。"),
    "Frame": "坐标系",
    "Dome reads raised": "圆顶呈凸起",
    "Rotated 90° anticlockwise": "逆时针旋转 90°",
    "Reflected about U = V": "关于 U = V 反射",
    "Decoded normal (x, y)": "解码出的法线 (x, y)",
    "On the diagonal: stays out (raised)": "对角线上：仍朝外（凸起）",
    "Turns in (dented)": "转向内（凹陷）",
    # Fig. 8, the worked example
    "One triangle in UV space and in game": "UV 空间中与游戏内的一个三角形",
    ("The worked example's triangle twice. Left, in UV space with U to the right and V down: p0 at the corner, p1 0.5 "
     "to the right, p2 0.25 down. Right, in game seen from below, with x to the right, -z up and the normal N out of "
     "the screen: the edge e1 along the partial derivative along U, e2 along the partial derivative along V, the "
     "tangent T pointing down along +V, N x T pointing left by the left-hand rule, and B = W(N x T) with W = -1 "
     "pointing right, along +U, as in the UV panel."):
        ("算例中的三角形，画了两次。左：UV 空间，U 向右，V 向下：p0 在角上，p1 向右 0.5，p2 向下 0.25。右：游戏内"
         "从下方看，x 向右，-z 向上，法线 N 指向屏幕外：边 e1 沿 U 方向的偏导数，e2 沿 V 方向的偏导数，切线 T 沿 +V "
         "向下，N × T 按左手定则指向左方，B = W(N × T)（W = -1）指向右方，沿 +U，与 UV 面板一致。"),
    "UV space": "UV 空间",
    "U right, V down": "U 向右，V 向下",
    "e₁, along ∂p/∂u": "e₁，沿 ∂p/∂u",
    "e₂, along ∂p/∂v": "e₂，沿 ∂p/∂v",
    "In game, seen from below": "游戏内，从下方看",
    "x right, −z up, N out of the screen": "x 向右，−z 向上，N 指向屏幕外",
    "B = W(N × T), along +U": "B = W(N × T)，沿 +U",
    "N × T (left-hand rule), W = −1": "N × T（左手定则），W = −1",
    # Fig. 10, the channel changes
    "Matching the map to tangents along +U": "使贴图与沿 +U 的切线相匹配",
    ("Two columns, without a mirror and with Z mirrored, each with two domes seen from above. Top: the map as "
     "authored, read through tangents along +U: without a mirror every normal is rotated by 90 degrees anticlockwise "
     "and points sideways; with Z mirrored every normal is reflected about the line U = V, so the normals on that "
     "diagonal point outward and those on the other diagonal inward. Bottom: the map after the channel change, (20) "
     "or (21): every normal points outward, as authored. The changes are derived from the measured frames, not "
     "tested in game."):
        ("两列，分别为无镜像和 Z 轴镜像，每列有两个从上方看的圆顶。上：按原样制作的贴图，经沿 +U 的切线读取：无镜像"
         "时每条法线逆时针旋转 90 度，指向侧面；Z 轴镜像时每条法线关于直线 U = V 反射，该对角线上的法线朝外，另一条"
         "对角线上的朝内。下：通道变换 (20) 或 (21) 之后的贴图：每条法线都朝外，与制作时一致。这些变换由实测的切线"
         "坐标系推导得出，未在游戏内测试。"),
    "Without a mirror": "无镜像",
    "Map as authored: rotated 90° anticlockwise": "原样贴图：逆时针旋转 90°",
    "After (20): outward, as authored": "经 (20) 变换后：朝外，与制作时一致",
    "With Z mirrored": "Z 轴镜像",
    "Map as authored: reflected about U = V": "原样贴图：关于 U = V 反射",
    "After (21): outward, as authored": "经 (21) 变换后：朝外，与制作时一致",
    "Outward (raised)": "朝外（凸起）",
    "Inward (dented)": "朝内（凹陷）",
    "Sideways": "侧向",
    "Derived from the measured frames; not tested in game.": "由实测的切线坐标系推导得出；未在游戏内测试。",
    # Fig. 11, the ways out of Blender
    "Ways out of Blender": "从 Blender 导出的途径",
    ("Two routes from Blender into the importer: Blender's FBX export with Tangent Space off, with no tangents, and "
     "with Tangent Space on, with tangents along +U and no W. With ER Tangents, the importer writes a FLVER whose "
     "tangents follow the game's frame, whichever route the file took."):
        ("从 Blender 到导入器的两条途径：Blender 的 FBX 导出关闭 Tangent Space 时不含切线，开启 Tangent Space 时含有"
         "沿 +U 的切线且没有 W。使用 ER Tangents 时，无论文件经由哪条途径，导入器写出的 FLVER 中的切线都遵循游戏的"
         "切线坐标系。"),
    "FBX export": "FBX 导出",
    "Tangent Space off": "关闭 Tangent Space",
    "no tangents": "不含切线",
    "Tangent Space on": "开启 Tangent Space",
    "+U tangents with no W": "沿 +U 的切线，没有 W",
    "Importer": "导入器",
    "with ER Tangents": "使用 ER Tangents",
    "FLVER": "FLVER",
    "the game's frame": "游戏的切线坐标系",
}

ELEMENT = re.compile(r"(<(text|title|desc)\b[^>]*>)(.*?)(</\2>)", re.S)
TAG = re.compile(r"(<[^>]+>)")


def _translate_piece(piece):
    """One run of character data in Chinese, keeping the whitespace around it."""
    text = html.unescape(piece).strip()
    if not text or text not in ZH:
        return piece
    start = piece[:len(piece) - len(piece.lstrip())]
    end = piece[len(piece.rstrip()):]
    return start + html.escape(ZH[text], quote=False) + end


def translate(svg):
    """
    A figure's SVG with its text in Chinese.

    Only the character data of ``<text>``, ``<title>`` and ``<desc>`` changes;
    child elements (such as an ``<animate>`` inside a label) are kept, and text
    that is only symbols or numbers, or is not in ``ZH``, stays as it is. The
    font stack gains Chinese faces.

    Parameters
    ----------
    svg : str

    Returns
    -------
    str
    """
    def element(match):
        opening, _, body, closing = match.groups()
        parts = TAG.split(body)
        return opening + "".join(p if TAG.fullmatch(p) else _translate_piece(p) for p in parts) + closing

    return ELEMENT.sub(element, svg).replace(FONT_STACK, ZH_FONT_STACK)


def zh_name(name):
    """The Chinese file's name: ``paper_x.svg`` becomes ``paper_x.zh.svg``."""
    return name[:-len(".svg")] + ".zh.svg"


def build(english):
    """
    The paper's figures in Chinese.

    Parameters
    ----------
    english : dict
        File name to SVG text, as ``make_figures`` builds them.

    Returns
    -------
    dict
        ``<name>.zh.svg`` to SVG text, for each name in ``PAPER_FIGURES``.
    """
    return {zh_name(name): translate(english[name]) for name in PAPER_FIGURES}
