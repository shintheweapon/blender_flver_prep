# Every report and interface text of the add-on that is formatted with fields,
# as templates; plain Python. The templates are also the keys of the translations.

# Panel
ARMATURE = "Armature: {name}"
NO_ARMATURE = "No armature selected"

# Reports of Prepare Copy
SELECT_ARMATURE = "Select an armature first"
NO_MESHES = "{name} has no meshes"
OBJECT_MODE = "Switch to Object Mode first"
PREPARED_MIRRORED = ("Prepared {count} meshes in collection {collection}. "
                     "Mirror Z already applied: set Transform to None in FbxImporter")
PREPARED_PLAIN = ("Prepared {count} meshes in collection {collection}. "
                  "Set Transform to Mirror Z in FbxImporter")

# Reports of Prepare and Export, and Export Copy
RUN_PREPARE_FIRST = "Run Prepare Copy first"
EXPORT_FAILED = "Export failed: {error}"
EXPORTED_MIRRORED = ("Exported {count} meshes from {collection} to {path}. "
                     "Mirror Z already applied: set Transform to None in FbxImporter")
EXPORTED_PLAIN = ("Exported {count} meshes from {collection} to {path}. "
                  "Set Transform to Mirror Z in FbxImporter")

# Reports of Remove Vertex Colors
REMOVED_COLORS = "Removed {count} color attributes from {meshes} meshes"
REMOVED_COLORS_KEPT = ("Removed {count} color attributes from {meshes} meshes. "
                       "Kept the render color on {kept} meshes")
NO_COLORS = "No color attributes to remove"


def templates() -> dict:
    """
    List every message template of this module.

    Returns
    -------
    dict
        Constant name to template, for every upper-case string constant.
    """
    return {name: value for name, value in globals().items()
            if name.isupper() and isinstance(value, str)}
