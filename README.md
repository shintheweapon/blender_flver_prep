# FS FBX Tools

A Blender add-on that prepares models for [The12thAvenger's FbxImporter](https://github.com/The12thAvenger/FbxImporter),
which imports FBX meshes into FromSoftware FLVER files.

Requires Blender 4.5 or later.

## What FbxImporter expects

FbxImporter reads each mesh's raw vertex coordinates from the FBX file. It does not apply the file's axis settings,
its unit scale, or any object, parent or bone transform; it matches bones by name only. So the mesh data itself must
already be:
- Y up, with 1 unit = 1 metre;
- in the armature's rest (bind) pose, at its final place;
- in Blender's FBX axis conversion (Forward -Z, Up Y), where FbxImporter's **Mirror Z** then gives FLVER
  coordinates.

Blender keeps mesh data Z up and stores each object's position, rotation and scale separately, so a Blender model
does not meet these rules as it is. **Prepare Copy** makes a copy that does.

## Install

1. Build `dist\fs_fbx_tools-1.0.0.zip` (see [Build](#build)).
2. In Blender: **Edit > Preferences > Get Extensions**, open the menu at the top right, choose **Install from Disk**
   and pick the zip.

## Prepare Copy

In the 3D Viewport, open the sidebar (N) and the **FS FBX** tab. Select an armature in Object mode, set the options,
then press **Prepare Copy**.

It makes the collection `<armature>_fs` holding:
- a copy of the armature, `<armature>_fs`, with the same bone names;
- a copy of each of its meshes, `<mesh>_fs`: the armature's children and the meshes whose Armature modifier targets
  it.

The armature copy is shown In Front (Object Properties > Viewport Display > In Front), so its bones are drawn over
the meshes.

Each mesh copy holds the original:
- in the armature's rest pose, even when the armature is posed;
- with its other modifiers (for example Subdivision) applied;
- multiplied by its world transform and the FBX axis conversion, so the copy itself has no transform.

The copies share the originals' materials and keep their vertex groups. In Blender's Z up view the copies lie on
their back: that is the orientation FbxImporter needs. Running Prepare Copy again on the same armature replaces its
`_fs` collection. The originals are not changed.

### Options

Both options match FbxImporter's options of the same names. Use each in one place only.

| Option | What it does | Then in FbxImporter |
|---|---|---|
| **Mirror Z** | Negates Z of positions and normals and keeps each face's corner order. The copy is then in FLVER coordinates. | Leave Mirror Z off |
| (Mirror Z off) | | Tick Mirror Z |
| **Flip Faces** | Reverses each face's corner order; normals stay as they were. | Leave Flip Faces off |

The options are off by default. Blender remembers them between sessions with its preferences. The report after
Prepare Copy says which Mirror Z setting to use in FbxImporter.

### Names

Blender gives every object a unique name, so the copies end in `_fs`, and the exported file keeps those names.
FbxImporter names each mesh and its material after the object name, and looks for a node of that name: a mesh
`Body_fs` gets a new node `Body_fs` instead of reusing a node `Body`. Bone names have no suffix, so weights still find
their bones. Rename the meshes afterwards (for example in FLVER_Editor) when you need the original names.

## Export

Two more buttons in the **FS FBX** tab write the `_fs` collection to an FBX file; both open a file dialog:
- **Prepare and Export...** runs Prepare Copy with the current options, then exports the new collection;
- **Export Copy...** exports the `_fs` collection that already exists for the selected armature (the original or
  its `_fs` copy). Without one it stops with "Run Prepare Copy first".

The file holds the collection's armature and meshes exactly as they are in Blender: the same vertex positions,
normals and corner order, with identity object transforms. Blender's FBX exporter is used with:
- Forward Y, Up Z (no axis conversion);
- Apply Transform off and Apply Scalings "FBX Units Scale" (no scaling of the vertices);
- armatures and meshes only, no leaf bones.

The report names the Mirror Z setting to use in FbxImporter, from the options the collection was made with. The
selection and active object are restored after the export.

## Y-Up View

The copies lie on their back in Blender's usual views. Three buttons in the **FS FBX** tab turn the 3D Viewport to an
orthographic view that shows them upright. The axis in each name is the side the viewer is on:

| Button | Looks | Screen up | Screen right |
|---|---|---|---|
| Front (-Z, Y-Up) | from -Z towards +Z | +Y | -X |
| Side (-X, Y-Up) | from -X towards +X | +Y | +Z |
| Top (+Y, Y-Up) | from +Y down towards -Y | +Z | -X |

Front is the same as Ctrl+Numpad 7 (Bottom) followed by a 180° roll. The views are fixed: on a copy made with Mirror Z
off, the character faces +Z, so Front shows its back; with Mirror Z on, it shows its face.

## Remove Vertex Colors

**Remove Vertex Colors**, at the bottom of the **FS FBX** tab, removes every Color Attribute (vertex color) from the
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
- `view.py`: the rotations of the Y-up views (no user interface);
- `colors.py`: removes a mesh's color attributes (no user interface);
- `operator.py`: the Prepare Copy, Prepare and Export, Export Copy, Y-Up View and Remove Vertex Colors commands;
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

It runs Blender's extension build on `src` and writes `dist\fs_fbx_tools-<version>.zip`, then checks the zip's
layout. Pass `-Blender "<path to blender.exe>"` when Blender is elsewhere.

## License

GPL-3.0-or-later; see [LICENSE](LICENSE).
