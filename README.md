# FLVER Prep

A Blender add-on that prepares models for [The12thAvenger's FbxImporter](https://github.com/The12thAvenger/FbxImporter),
which imports FBX meshes into FromSoftware FLVER files.

Requires Blender 4.5 or later.

## What FbxImporter expects

FbxImporter reads each mesh's raw vertex coordinates from the FBX file. It does not apply the file's axis settings,
its unit scale, or any object, parent or bone transform; it matches bones by name only. So the mesh data itself must
already be:
- Y up, with 1 unit = 1 metre;
- in the armature's rest (bind) pose, at its final place;
- in Blender's FBX axis conversion (Forward -Z, Up Y), where FbxImporter's **Transform: Mirror Z** then gives
  FLVER coordinates.

Blender keeps mesh data Z up and stores each object's position, rotation and scale separately, so a Blender model
does not meet these rules as it is. **Prepare Copy** makes a copy that does.

## Install

1. Download `flver_prep-1.0.0.zip` from this repository's Releases page, or build it (see [Build](#build)).
   If FS FBX Tools or FS Export Prep, earlier names of this add-on, is installed, uninstall it first.
2. In Blender: **Edit > Preferences > Get Extensions**, open the menu at the top right, choose **Install from Disk**
   and pick the zip.

## Prepare Copy

In the 3D Viewport, open the sidebar (N) and the **FLVER Prep** tab. Select an armature in Object mode, set the options,
then press **Prepare Copy**.

It makes the collection `<armature>_fs` holding:
- a copy of the armature, `<armature>_fs`, with the same bone names;
- a copy of each of its meshes, `<mesh>_fs`: the armature's children and the meshes whose Armature modifier targets
  it.

The armature copy is shown In Front (Object Properties > Viewport Display > In Front), so its bones are drawn over
the meshes.

The copies keep the originals' collections. Inside `<armature>_fs`, each collection that holds the armature or one of
its meshes is recreated as `<collection>_fs`, with the same Outliner colour tag, and each copy is linked where its
original is. The collections that the armature and all its meshes share at the top are left out. For example,
Character > {armature, Body > [Body], Clothes > [Shirt]} gives `<armature>_fs` > {armature copy, `Body_fs` >
[`Body_fs`], `Clothes_fs` > [`Shirt_fs`]}. The recreated collections are always visible, even when an original is
hidden or excluded, so that Export can include every copy.

Each mesh copy holds the original:
- in the armature's rest pose, even when the armature is posed;
- with its other modifiers (for example Subdivision) applied;
- multiplied by its world transform and the FBX axis conversion, so the copy itself has no transform.

The copies share the originals' materials and keep their vertex groups. In Blender's Z up view the copies lie on
their back: that is the orientation FbxImporter needs. Running Prepare Copy again on the same armature replaces its
`_fs` collection. The originals are not changed.

### Options

Both options match FbxImporter's options of the same names: Mirror Z is one of its **Transform** settings, Flip Faces
a check box. Use each in one place only.

| Option | What it does | Then in FbxImporter |
|---|---|---|
| **Mirror Z** | Negates Z of positions and normals and keeps each face's corner order. The copy is then in FLVER coordinates. | Set Transform to None |
| (Mirror Z off) | | Set Transform to Mirror Z |
| **Flip Faces** | Reverses each face's corner order; normals stay as they were. | Leave Flip Faces off |

The options are off by default. Blender remembers them between sessions with its preferences. The report after
Prepare Copy says which Transform setting to use in FbxImporter.

FbxImporter 1.10 and earlier have a Mirror check box instead: leave it off for None, tick it for Mirror Z.
The **Blender/3ds Max** Transform setting is not for FLVER Prep's output, which is already Y up.

### Names

Blender gives every object a unique name, so the copies end in `_fs`, and the exported file keeps those names.
FbxImporter names each mesh and its material after the object name, and looks for a node of that name: a mesh
`Body_fs` gets a new node `Body_fs` instead of reusing a node `Body`. Bone names have no suffix, so weights still find
their bones. Rename the meshes afterwards (for example in FLVER_Editor) when you need the original names.

## Export

Two more buttons in the **FLVER Prep** tab write the `_fs` collection to an FBX file; both open a file dialog:
- **Prepare and Export...** runs Prepare Copy with the current options, then exports the new collection;
- **Export Copy...** exports the `_fs` collection that already exists for the selected armature (the original or
  its `_fs` copy). Without one it stops with "Run Prepare Copy first".

The file holds the collection's armature and meshes exactly as they are in Blender: the same vertex positions,
normals and corner order, with identity object transforms. Blender's FBX exporter is used with:
- Forward Y, Up Z (no axis conversion);
- Apply Transform off and Apply Scalings "FBX Units Scale" (no scaling of the vertices);
- armatures and meshes only, no leaf bones.

The report names the Transform setting to use in FbxImporter, from the options the collection was made with. The
selection and active object are restored after the export.

## Y-Up View

The copies lie on their back in Blender's usual views. Under **Y-Up Views** in the **FLVER Prep** tab, six buttons turn
the 3D Viewport to an orthographic view that shows them upright. The axis in each name is the side the viewer is on:

| Button | Looks | Screen up | Screen right |
|---|---|---|---|
| Face or Back (-Z) | from -Z towards +Z | +Y | -X |
| Face or Back (+Z) | from +Z towards -Z | +Y | +X |
| Left (-X) | from -X towards +X | +Y | +Z |
| Right (+X) | from +X towards -X | +Y | -Z |
| Top (+Y) | from +Y down towards -Y | +Z | -X |
| Bottom (-Y) | from -Y up towards +Y | -Z | -X |

Each opposite view is its partner turned half a turn, as in Blender's own views: (+Z) is (-Z) turned about the screen's
up, Right is Left turned about the screen's up, and Bottom is Top turned about the screen's right. The (-Z) view is the
same as Ctrl+Numpad 7 (Bottom) followed by a 180° roll.

### Face and Back

The first row names the two Z views by the side of the character they show: **Face** on the left, **Back** on the
right. A character whose original faces -Y in Blender faces:
- +Z in a copy made with Mirror Z off;
- -Z in a copy made with Mirror Z on.

The Mirror Z setting comes from the `_fs` collection of the active object (the original armature or its copy). When
the active object has no `_fs` collection, the Mirror Z option in the tab is used. An original that faces +Y gets Face
and Back swapped.

### Side Up

**Side Up** sets which way Left and Right are turned, and is remembered between sessions like Mirror Z:

| Side Up | Left (-X): up, right | Right (+X): up, right |
|---|---|---|
| Y-Up | +Y, +Z | +Y, -Z |
| Z-Down | -Z, +Y | -Z, -Y |

Left with Z-Down is Left with Y-Up rolled 90° clockwise.

### Roll

**Anti-clockwise** and **Clockwise** turn the picture of the current view 90°, about the viewing direction. They work on
any view and keep its perspective setting, and turn the same way as Blender's Shift+Numpad 4 and Shift+Numpad 6.

## Remove Vertex Colors

**Remove Vertex Colors**, at the bottom of the **FLVER Prep** tab, removes every Color Attribute (vertex color) from the
meshes in one click, whatever its domain (point or face corner) and type (byte or float). It works in Object mode,
and Ctrl+Z brings the colors back. Two options, remembered between sessions like Mirror Z and Flip Faces:

| Option | Meaning | Default |
|---|---|---|
| Meshes | Selected Meshes (every selected mesh) or Active Mesh (only the active one) | Selected Meshes |
| Keep Render Color | Keep the render color: the one marked with the camera icon in Properties > Data > Color Attributes | off |

## Limits

- The scene's unit scale is taken to be 1.0 (one Blender unit = one metre).
- With Mirror Z, bone heads and tails are mirrored exactly; bone roll is whatever Blender keeps. FbxImporter does not
  use bone roll.

## Develop

The add-on's files are in `src/`:
- `prepare.py`: the conversion (no user interface);
- `export.py`: writes a prepared collection to FBX (no user interface);
- `view.py`: the rotations of the Y-up views and the roll (no user interface);
- `colors.py`: removes a mesh's color attributes (no user interface);
- `operator.py`: the Prepare Copy, Prepare and Export, Export Copy, Y-Up View, Roll View and Remove Vertex Colors commands;
- `panel.py`: the sidebar panel;
- `prefs.py`: the options;
- `messages.py`, `i18n_zh_hans.py`: texts and their Simplified Chinese translation;
- `__init__.py`: registration.

### Test

```
blender.exe -b -P tests\run_tests.py
```

The runner sets the interface language to English for the run, because the tests check English texts.

### Build

```
.\build.ps1
```

It runs Blender's extension build on `src` and writes `dist\flver_prep-<version>.zip`, then checks the zip's
layout. It needs the path to your blender.exe: pass it with `.\build.ps1 -Blender "<path to blender.exe>"`, or put it
on the first line of `build.local.txt` next to `build.ps1` (git-ignored, so the path stays on your machine).

## License

GPL-3.0-or-later; see [LICENSE](LICENSE).
