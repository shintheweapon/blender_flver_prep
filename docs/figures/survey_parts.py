"""
The run behind docs/paper/ER_NORMAL_MAPS.md, Section IV-B: every FLVER under a
folder of unpacked game parts is dumped as JSON with the dumper in
``flverdump/`` and surveyed with ``frame_survey.part_survey``, and the results
are written to ``frame_survey.json``.

Run ``python docs/figures/survey_parts.py <flverdump executable> <folder>``.
Progress is kept in ``frame_survey_progress.jsonl`` inside that folder, so a
stopped run resumes; each dump is deleted once surveyed. See
docs/paper/README.md for the steps before it.
"""

import json
import os
import subprocess
import sys

import frame_survey

PROGRESS = "frame_survey_progress.jsonl"
DUMP = "frame_survey_dump.json"


def flver_paths(folder):
    """
    Every ``.flver`` under a folder, one per file name.

    Parameters
    ----------
    folder : str

    Returns
    -------
    list of str
        Paths in sorted order (case ignored); of files with the same name, the
        first in that order.
    """
    found = []
    for root, _, names in os.walk(folder):
        found += [os.path.join(root, name) for name in names if name.lower().endswith(".flver")]
    seen, unique = set(), []
    for path in sorted(found, key=str.lower):
        name = os.path.basename(path).lower()
        if name not in seen:
            seen.add(name)
            unique.append(path)
    return unique


def main(dumper, folder):
    """
    Survey every FLVER under a folder and write ``frame_survey.json``.

    Parameters
    ----------
    dumper : str
        The built ``flverdump`` executable.
    folder : str
        A folder of unpacked game parts.

    Returns
    -------
    list of str
        The FLVERs that could not be dumped, with the dumper's message.
    """
    progress_path, dump_path = os.path.join(folder, PROGRESS), os.path.join(folder, DUMP)
    done = set()
    if os.path.exists(progress_path):
        with open(progress_path, encoding="utf-8") as file:
            done = {json.loads(line)["file"] for line in file}
    paths = flver_paths(folder)
    with open(progress_path, "a", encoding="utf-8") as progress:
        for index, path in enumerate(paths, 1):
            name = os.path.splitext(os.path.basename(path))[0]
            if name in done:
                continue
            run = subprocess.run([dumper, path, dump_path], capture_output=True, text=True)
            if run.returncode != 0:
                lines = run.stderr.strip().splitlines()
                entry = {"file": name, "survey": None, "error": lines[-1] if lines else str(run.returncode)}
            else:
                with open(dump_path, encoding="utf-8") as file:
                    entry = {"file": name, "survey": frame_survey.part_survey(name, json.load(file))}
                os.remove(dump_path)
            progress.write(json.dumps(entry) + "\n")
            progress.flush()
            if index % 100 == 0:
                print(f"{index} of {len(paths)}", flush=True)
    parts, failed = [], []
    with open(progress_path, encoding="utf-8") as file:
        for line in file:
            entry = json.loads(line)
            if entry.get("error"):
                failed.append(f"{entry['file']}: {entry['error']}")
            elif entry["survey"]:
                parts.append(entry["survey"])
    frame_survey.write(parts)
    return failed


if __name__ == "__main__":
    for message in main(sys.argv[1], sys.argv[2]):
        print("not read:", message)
