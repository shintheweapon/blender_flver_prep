# Changelog

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
