# Changelog

## 1.0.0

### Added
- **Prepare and Export...** and **Export Copy...** buttons in the FLVER Prep tab: write the `<armature>_fs` collection
  to an FBX file as it is (same vertex positions, normals and corner order; identity object transforms), using Blender's
  FBX exporter with Forward Y, Up Z, no Apply Transform and FBX Units Scale. Names keep the `_fs` suffix.
- The report after an export names the Mirror Z setting to use in FbxImporter; Prepare Copy now records its options
  on the collection for this.
- Prepare Copy shows the armature copy In Front, so its bones are drawn over the meshes.
- The extension declares the `files` permission.
- **Y-Up Views** in the FLVER Prep tab: six buttons turn the 3D Viewport to a fixed orthographic view that shows the
  Y-up copies upright, from -Z, +Z, -X, +X, +Y and -Y. The Z views are named **Face** and **Back** after the side of the
  character they show, from the Mirror Z the active object's `_fs` collection was made with.
- **Side Up** (Y-Up or Z-Down) for the Left and Right views, remembered as an add-on preference.
- **Anti-clockwise** and **Clockwise** buttons: turn the current view 90°, as Blender's Shift+Numpad 4 and 6 do.
- **Remove Vertex Colors** button in the FLVER Prep tab: removes every Color Attribute from the selected meshes or the
  active mesh, optionally keeping the render color. Both options are add-on preferences.
- `docs/NORMAL_MAPS.md`: Elden Ring's normal-map layout and tangent convention, and how to get matching tangents
  through FbxImporter.

### Changed
- The reports and README name FbxImporter 1.11's **Transform** setting (None or Mirror Z) in place of its
  old Mirror check box.
- Named **FLVER Prep** (was FS FBX Tools); extension id `flver_prep`, sidebar tab **FLVER Prep**. Install it in
  place of FS FBX Tools, whose add-on preferences do not carry over.

### Fixed
- Command tooltips show in Chinese (Blender looks them up in the operator context).
- Prepare Copy keeps the originals' collections: each is recreated inside the `_fs` collection as `<collection>_fs`,
  below the collections the armature and all its meshes share. Before, every copy went straight into the `_fs`
  collection. Export includes the copies in the recreated collections, and running Prepare Copy again removes them.

## 0.1.0

### Added
- **Prepare Copy**, in the 3D Viewport sidebar tab "FS FBX": copies the active armature and its meshes into the
  collection `<armature>_fs`, converted into the space The12thAvenger's FbxImporter reads (Y up, metres, identity
  object transforms). Meshes are the armature's children and the meshes whose Armature modifier targets it.
- Meshes are copied in the armature's rest pose with their other modifiers applied; materials are shared; vertex
  groups and bone names are kept; copied objects end in `_fs`.
- **Mirror Z** and **Flip Faces** options, matching FbxImporter's options of the same names, remembered as add-on
  preferences (off by default).
- Running it again on the same armature replaces its previous `_fs` collection.
- Simplified Chinese interface (zh_HANS), using Blender's own words.
