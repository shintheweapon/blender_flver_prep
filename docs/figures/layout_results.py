"""
The results of the layout test (``integrability``) on vanilla normal maps, as
committed in ``integrability_maps.json``: reading them and summarising them
per file-name prefix, for the paper's Section IV-A and its figure. Plain
Python, so the figures build without numpy or the game files.
"""

import json
import os
import statistics

FIGURES_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(FIGURES_DIR, "integrability_maps.json")

OUTCOMES = ("directx+", "directx-", "swapped+", "swapped-")
UNTESTABLE = "untestable"
# File-name prefixes whose part kind is known; the others are written as the prefix alone
KINDS = {"WP": "weapons", "BD": "body", "HD": "head", "LG": "legs", "AM": "arms"}


def prefix(name):
    """The part kind's file-name prefix: the first two letters, upper case."""
    return name[:2].upper()


def summary(maps):
    """
    The results per file-name prefix, most maps first.

    Parameters
    ----------
    maps : list of dict
        The ``maps`` of ``integrability_maps.json``.

    Returns
    -------
    list of dict
        Per prefix: ``prefix``, ``tested`` (testable maps), ``untestable``,
        ``count`` per outcome in ``OUTCOMES``, ``directx_median`` and
        ``swapped_median`` (median whole-map correlations) and
        ``tile_share_median`` (median share of a map's tested tiles won by
        DirectX with a positive sign), over the testable maps.
    """
    groups = {}
    for entry in maps:
        groups.setdefault(prefix(entry["name"]), []).append(entry)
    rows = []
    for key, entries in groups.items():
        testable = [e for e in entries if e["outcome"] != UNTESTABLE]
        shares = [e["tiles"]["directx+"] / sum(e["tiles"][o] for o in OUTCOMES) for e in testable]
        rows.append({
            "prefix": key, "tested": len(testable), "untestable": len(entries) - len(testable),
            "count": {o: sum(e["outcome"] == o for e in testable) for o in OUTCOMES},
            "directx_median": statistics.median(e["directx"] for e in testable),
            "swapped_median": statistics.median(e["swapped"] for e in testable),
            "tile_share_median": statistics.median(shares),
        })
    rows.sort(key=lambda row: (-(row["tested"] + row["untestable"]), row["prefix"]))
    return rows


def load():
    """
    The committed results.

    Returns
    -------
    dict
        The contents of ``integrability_maps.json``.
    """
    with open(RESULTS, encoding="utf-8") as file:
        return json.load(file)
