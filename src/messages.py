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
                     "Mirror Z already applied: leave it off in FbxImporter")
PREPARED_PLAIN = ("Prepared {count} meshes in collection {collection}. "
                  "Tick Mirror Z in FbxImporter")


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
