"""
The survey of docs/paper/ER_NORMAL_MAPS.md, Section IV-B: the check of
``frame_checks`` run on every mesh of every vanilla part, and its summaries
per file-name prefix and per exception.

A part is given as the meshes a FLVER reader dumps: per mesh, its material
name and its vertices (position ``p``, normal ``n``, tangents ``t`` as
``(x, y, z, w)``, UV sets ``uv``) and the LOD0 triangles as a flat list of
vertex indices. Reading the game file is left to the caller. The check uses
the first tangent and the first UV set, as the paper does.

Run ``python docs/figures/frame_survey.py <dump.json> ...`` to survey dumped
parts (each named after its file) and rewrite ``frame_survey.json`` next to
this script. The JSON holds part, mesh and material names and numbers only,
no paths.
"""

import json
import os
import sys

from frame_checks import frame_checks, summarise

FIGURES_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(FIGURES_DIR, "frame_survey.json")
SIGNS = {"+": 1, "-": -1}
EXCEPTION_SHARE = 0.05
CLOTH_RULE_SHARE = 0.95
KEEPS = "keeps -1"
FOLLOWS = "follows (9)"
MIXED = "mixed"


def file_name(path):
    """
    The file name at the end of a material path: the text after the last
    backslash or slash.

    Parameters
    ----------
    path : str

    Returns
    -------
    str
    """
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def mesh_corners(mesh):
    """
    The corners of one dumped mesh, checked by ``frame_checks``.

    Parameters
    ----------
    mesh : dict
        ``vertices`` and ``triangles`` as described in the module docstring.

    Returns
    -------
    list of frame_checks.Corner
        Empty when the mesh has no triangles, tangents or UVs.
    """
    vertices, flat = mesh["vertices"], mesh["triangles"]
    if not vertices or not flat or not vertices[0]["t"] or not vertices[0]["uv"]:
        return []
    return frame_checks([v["p"] for v in vertices], [v["n"] for v in vertices], [v["uv"][0] for v in vertices],
                        [tuple(flat[i:i + 3]) for i in range(0, len(flat) - 2, 3)],
                        [tuple(v["t"][0]) for v in vertices])


def _held(corners):
    """Per UV orientation, ``[corners where (9) holds, corners]``."""
    return {key: [sum(c.w_rule for c in corners if c.uv_sign == sign), sum(c.uv_sign == sign for c in corners)]
            for key, sign in SIGNS.items()}


def part_survey(name, meshes):
    """
    The survey of one part.

    Parameters
    ----------
    name : str
        The part's file name without its extension, such as ``BD_M_1730``.
    meshes : list of dict
        The part's dumped meshes.

    Returns
    -------
    dict or None
        ``name``; over all its corners: ``corners``, ``w_exact`` (every W is
        exactly +1 or -1), ``length`` (min, max), ``normal_dot_99``,
        ``v_cos_median`` and ``held`` (see ``_held``); and ``meshes``, per
        mesh with corners: ``index``, ``material``, ``corners`` and ``held``.
        None when no mesh has corners.
    """
    every, per_mesh = [], []
    for index, mesh in enumerate(meshes):
        corners = mesh_corners(mesh)
        if corners:
            every += corners
            per_mesh.append({"index": index, "material": mesh["material"], "mtd": file_name(mesh.get("mtd", "")),
                             "corners": len(corners), "held": _held(corners)})
    if not every:
        return None
    values = summarise(every)
    return {"name": name, "corners": len(every), "w_exact": all(abs(w) == 1 for w in values["w_values"]),
            "length": [round(x, 4) for x in values["length"]], "normal_dot_99": round(values["normal_dot_99"], 4),
            "v_cos_median": None if values["v_cos_median"] is None else round(values["v_cos_median"], 4),
            "held": _held(every), "meshes": per_mesh}


def write(parts):
    """
    Write the survey, parts sorted by name.

    Parameters
    ----------
    parts : list of dict
        From ``part_survey``.
    """
    with open(RESULTS, "w", encoding="utf-8", newline="\n") as file:
        json.dump({"parts": sorted(parts, key=lambda part: part["name"].lower())}, file, indent=1)
        file.write("\n")


def load():
    """
    The committed survey.

    Returns
    -------
    list of dict
        The parts.
    """
    with open(RESULTS, encoding="utf-8") as file:
        return json.load(file)["parts"]


def prefix(name):
    """The part kind's file-name prefix: the first two letters, upper case."""
    return name[:2].upper()


def summary_by_prefix(parts):
    """
    The survey per file-name prefix, most parts first.

    Parameters
    ----------
    parts : list of dict

    Returns
    -------
    list of dict
        Per prefix: ``prefix``, ``parts``, ``corners``, ``w_exact`` (on every
        part), ``length`` (min, max over the parts), ``normal_dot_99`` (the
        largest part value), ``v_cos_median`` (the smallest part value) and
        ``held`` (pooled over the parts).
    """
    groups = {}
    for part in parts:
        groups.setdefault(prefix(part["name"]), []).append(part)
    rows = []
    for key, members in groups.items():
        medians = [p["v_cos_median"] for p in members if p["v_cos_median"] is not None]
        rows.append({
            "prefix": key, "parts": len(members), "corners": sum(p["corners"] for p in members),
            "w_exact": all(p["w_exact"] for p in members),
            "length": [min(p["length"][0] for p in members), max(p["length"][1] for p in members)],
            "normal_dot_99": max(p["normal_dot_99"] for p in members),
            "v_cos_median": min(medians) if medians else None,
            "held": {s: [sum(p["held"][s][i] for p in members) for i in (0, 1)] for s in SIGNS},
        })
    rows.sort(key=lambda row: (-row["parts"], row["prefix"]))
    return rows


def is_cloth(material):
    """True for a material whose name contains "cloth" (any case)."""
    return "cloth" in material.lower()


def by_cloth(parts):
    """
    Where (9) holds, pooled over the meshes with a cloth material and over
    all other meshes.

    Parameters
    ----------
    parts : list of dict

    Returns
    -------
    dict
        ``cloth`` and ``other``: each ``meshes``, ``parts`` (with at least
        one such mesh) and ``held`` (see ``_held``).
    """
    groups = {key: {"meshes": 0, "parts": set(), "held": {s: [0, 0] for s in SIGNS}} for key in ("cloth", "other")}
    for part in parts:
        for mesh in part["meshes"]:
            group = groups["cloth" if is_cloth(mesh["material"]) else "other"]
            group["meshes"] += 1
            group["parts"].add(part["name"])
            for s in SIGNS:
                for i in (0, 1):
                    group["held"][s][i] += mesh["held"][s][i]
    for group in groups.values():
        group["parts"] = len(group["parts"])
    return groups


def mesh_behaviour(entry, share=CLOTH_RULE_SHARE):
    """
    How one surveyed mesh stores W on its corners with d > 0, where (9) asks
    for W = +1 with FLVER's winding.

    Parameters
    ----------
    entry : dict
        A mesh entry of ``part_survey``.
    share : float
        The share of those corners that decides.

    Returns
    -------
    str or None
        ``KEEPS`` when (9) fails on at least ``share`` of them, ``FOLLOWS``
        when it holds on at least ``share``, ``MIXED`` otherwise, and None
        when the mesh has no corners with d > 0.
    """
    held, total = entry["held"]["+"]
    if total == 0:
        return None
    if held >= share * total:
        return FOLLOWS
    if total - held >= share * total:
        return KEEPS
    return MIXED


def cloth_rule(parts):
    """
    Whether "the material file name contains cloth" predicts ``KEEPS``.

    Parameters
    ----------
    parts : list of dict

    Returns
    -------
    dict
        ``counts``: per ``(file contains cloth, behaviour)`` the number of
        meshes with a behaviour; ``name_and_file_differ``: the meshes whose
        material name and material file disagree on containing "cloth", and
        ``file_right``: those of them on which the material file predicts the
        behaviour;
        ``disagreeing``: ``(part, index, material, mtd, behaviour)`` for each
        mesh that does not follow the rule (a cloth file that does not keep
        -1, or another file that does not follow (9)).
    """
    counts, differ, file_right, disagreeing = {}, 0, 0, []
    for part in parts:
        for mesh in part["meshes"]:
            behaviour = mesh_behaviour(mesh)
            if behaviour is None:
                continue
            cloth_file = is_cloth(mesh["mtd"])
            counts[(cloth_file, behaviour)] = counts.get((cloth_file, behaviour), 0) + 1
            follows_rule = behaviour == (KEEPS if cloth_file else FOLLOWS)
            if cloth_file != is_cloth(mesh["material"]):
                differ += 1
                file_right += follows_rule
            if not follows_rule:
                disagreeing.append((part["name"], mesh["index"], mesh["material"], mesh["mtd"], behaviour))
    return {"counts": counts, "name_and_file_differ": differ, "file_right": file_right, "disagreeing": disagreeing}


SMALL_MESH = 30
LARGE_MESH = 300


def misfits(parts):
    """
    The meshes that do not follow ``cloth_rule``, described.

    Parameters
    ----------
    parts : list of dict

    Returns
    -------
    dict
        ``meshes`` and ``corners`` (their corners with d > 0); ``small``: the
        misfits with fewer than ``SMALL_MESH`` such corners;
        ``large_other_mixed``: the ``MIXED`` meshes without a cloth material
        file and with at least ``LARGE_MESH`` such corners, with
        ``lowest_share`` (the lowest share of those corners where (9) holds)
        and ``gaps`` (per mesh, the difference between that share and the
        share on corners with d < 0); ``large_cloth_following``: ``(part,
        material file, corners)`` for cloth material files that follow (9)
        on at least ``LARGE_MESH`` such corners.
    """
    rows = []
    for part in parts:
        for mesh in part["meshes"]:
            behaviour = mesh_behaviour(mesh)
            if behaviour is not None and behaviour != (KEEPS if is_cloth(mesh["mtd"]) else FOLLOWS):
                rows.append((part["name"], mesh, behaviour))
    share = lambda held: held[0] / held[1]
    large_mixed = [m for _, m, b in rows if b == MIXED and not is_cloth(m["mtd"])
                   and m["held"]["+"][1] >= LARGE_MESH and m["held"]["-"][1]]
    return {
        "meshes": len(rows),
        "corners": sum(m["held"]["+"][1] for _, m, _ in rows),
        "small": sum(m["held"]["+"][1] < SMALL_MESH for _, m, _ in rows),
        "large_other_mixed": {
            "meshes": len(large_mixed),
            "lowest_share": min(share(m["held"]["+"]) for m in large_mixed) if large_mixed else None,
            "gaps": sorted(abs(share(m["held"]["+"]) - share(m["held"]["-"])) for m in large_mixed),
        },
        "large_cloth_following": [(n, m["mtd"], m["held"]["+"][1]) for n, m, b in rows
                                  if b == FOLLOWS and m["held"]["+"][1] >= LARGE_MESH],
    }


def exceptions(parts, share=EXCEPTION_SHARE):
    """
    The meshes on which (9) fails on more than a share of their corners,
    grouped by material name, most failing corners first.

    Parameters
    ----------
    parts : list of dict
    share : float
        The share of a mesh's corners above which it counts.

    Returns
    -------
    list of dict
        Per material name: ``material``, ``meshes`` (``(part, index)``
        pairs), ``failed`` and ``corners`` (summed over those meshes).
    """
    groups = {}
    for part in parts:
        for mesh in part["meshes"]:
            failed = sum(mesh["held"][s][1] - mesh["held"][s][0] for s in SIGNS)
            if failed > share * mesh["corners"]:
                group = groups.setdefault(mesh["material"], {"material": mesh["material"], "meshes": [],
                                                             "failed": 0, "corners": 0})
                group["meshes"].append((part["name"], mesh["index"]))
                group["failed"] += failed
                group["corners"] += mesh["corners"]
    return sorted(groups.values(), key=lambda g: (-g["failed"], g["material"]))


def main(paths):
    """
    Survey dumped parts and write the results.

    Parameters
    ----------
    paths : list of str
        Dump files, each named after its part.
    """
    parts = []
    for path in paths:
        with open(path, encoding="utf-8") as file:
            survey = part_survey(os.path.splitext(os.path.basename(path))[0], json.load(file))
        if survey:
            parts.append(survey)
    write(parts)


if __name__ == "__main__":
    main(sys.argv[1:])
