"""
The layout test of the paper docs/paper/ER_NORMAL_MAPS.md (Section IV-A): for
a height field the mixed partial derivatives are equal, so in the right layout
the partial derivative of red along V matches that of green along U.

Image columns run along +U and rows along +V (row 0 at the top). Two pairings
are compared:

- **DirectX:** red with U and green with V, so dR/dv is compared with dG/du;
- **swapped:** red with V and green with U, so dR/du is compared with dG/dv.

The pairing with the larger correlation (in absolute value) wins; its sign
says whether green runs along +V (positive) or is inverted (negative). A map
is untestable when a correlation is undefined (a channel without variation)
or when every tile is flat.

Run ``python docs/figures/integrability.py <folder>`` to test every
``*_n.dds`` file under a folder of unpacked game textures and rewrite
``integrability_maps.json`` next to this script. The JSON holds file names
and results only, no paths; ``layout_results`` reads and summarises it.
"""

import json
import math
import os
import sys

import numpy as np

from layout_results import OUTCOMES, RESULTS, UNTESTABLE

DIRECTX = "directx"
SWAPPED = "swapped"
TILE = 256
FLAT = 0.03


def correlation(a, b):
    """
    The correlation of two arrays over their more detailed half.

    Parameters
    ----------
    a, b : numpy.ndarray
        Arrays of the same shape.

    Returns
    -------
    float
        Pearson's correlation over the elements where ``|a| + |b|`` is above
        its median.
    """
    detail = np.abs(a) + np.abs(b)
    keep = detail > np.median(detail)
    return float(np.corrcoef(a[keep], b[keep])[0, 1])


def test(red, green):
    """
    Which pairing of channels and UV axes a normal map follows.

    Parameters
    ----------
    red, green : numpy.ndarray
        The channels, from 0 to 1, rows along +V.

    Returns
    -------
    tuple
        ``(pairing, directx, swapped)``: the winning pairing (``DIRECTX`` or
        ``SWAPPED``) and the correlation of each pairing, over the pixels
        where any of the four partial derivatives is above its median.
    """
    r_u, r_v = np.gradient(red, axis=1), np.gradient(red, axis=0)
    g_u, g_v = np.gradient(green, axis=1), np.gradient(green, axis=0)
    detail = np.abs(r_u) + np.abs(r_v) + np.abs(g_u) + np.abs(g_v)
    keep = detail > np.percentile(detail, 50)
    directx = float(np.corrcoef(r_v[keep], g_u[keep])[0, 1])
    swapped = float(np.corrcoef(r_u[keep], g_v[keep])[0, 1])
    return (DIRECTX if abs(directx) > abs(swapped) else SWAPPED), directx, swapped


def outcome(pairing, directx, swapped):
    """
    The outcome name of a test: the winning pairing and its sign.

    Returns
    -------
    str
        One of ``OUTCOMES``.
    """
    value = directx if pairing == DIRECTX else swapped
    return f"{pairing}{'+' if value > 0 else '-'}"


def tiles(red, green, size=TILE):
    """
    The test run tile by tile.

    Parameters
    ----------
    red, green : numpy.ndarray
        The channels, from 0 to 1.
    size : int
        Tile width and height in pixels.

    Returns
    -------
    dict
        Count per outcome in ``OUTCOMES``, and ``"skipped"``: tiles where both
        channels' standard deviation is below 0.03 (no detail to test).
    """
    counts = dict.fromkeys(OUTCOMES + ("skipped",), 0)
    height, width = red.shape
    for top in range(0, height, size):
        for left in range(0, width, size):
            r, g = red[top:top + size, left:left + size], green[top:top + size, left:left + size]
            if r.std() < FLAT and g.std() < FLAT:
                counts["skipped"] += 1
                continue
            counts[outcome(*test(r, g))] += 1
    return counts


def test_map(red, green):
    """
    The whole-map test and the tile counts of one map.

    Returns
    -------
    dict
        ``directx`` and ``swapped`` (whole-map correlations, None when
        undefined), ``outcome`` (one of ``OUTCOMES``, or ``UNTESTABLE``) and
        ``tiles`` (see ``tiles``).
    """
    pairing, directx, swapped = test(red, green)
    counts = tiles(red, green)
    defined = not (math.isnan(directx) or math.isnan(swapped))
    tested = sum(counts[o] for o in OUTCOMES) > 0
    return {"directx": round(directx, 4) if defined else None, "swapped": round(swapped, 4) if defined else None,
            "outcome": outcome(pairing, directx, swapped) if defined and tested else UNTESTABLE, "tiles": counts}


def normal_maps(folder):
    """
    Every ``*_n.dds`` under a folder, one per file name.

    Parameters
    ----------
    folder : str

    Returns
    -------
    list of str
        Paths in sorted order; of files with the same name (case ignored),
        the first in that order.
    """
    found = []
    for root, _, names in os.walk(folder):
        found += [os.path.join(root, name) for name in names if name.lower().endswith("_n.dds")]
    seen, unique = set(), []
    for path in sorted(found, key=str.lower):
        name = os.path.basename(path).lower()
        if name not in seen:
            seen.add(name)
            unique.append(path)
    return unique


def main(folder):
    """
    Test every normal map under a folder and write the results.

    Parameters
    ----------
    folder : str
        A folder of unpacked game textures.

    Returns
    -------
    list of str
        File names that could not be read.
    """
    from PIL import Image

    results, failed = [], []
    paths = normal_maps(folder)
    for index, path in enumerate(paths, 1):
        name = os.path.basename(path)
        try:
            with Image.open(path) as image:
                pixels = np.asarray(image.convert("RGBA"), dtype=float) / 255
        except Exception as error:  # noqa: BLE001 (any decoder failure is reported and skipped)
            failed.append(f"{name}: {error}")
            continue
        entry = {"name": name, "width": int(pixels.shape[1]), "height": int(pixels.shape[0])}
        entry.update(test_map(pixels[..., 0], pixels[..., 1]))
        results.append(entry)
        if index % 100 == 0:
            print(f"{index} of {len(paths)}", flush=True)
    with open(RESULTS, "w", encoding="utf-8", newline="\n") as file:
        json.dump({"tile": TILE, "flat": FLAT, "maps": results}, file, indent=1)
        file.write("\n")
    return failed


if __name__ == "__main__":
    for line in main(sys.argv[1]):
        print("not read:", line)
