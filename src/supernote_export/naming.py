"""Work out the output name for each converted note.

Supernote names a file by capture time (``YYYYMMDD_HHMMSS``). A note you rename
on the device keeps whatever stem you gave it. A timestamp stem becomes a
``YYYY-MM-DD`` date; any other stem is kept as it is. When two notes want the
same name in one output folder, the later one gets a ``-2``/``-3`` suffix.

A name you chose on the device outranks a generated one, so those stems are
reserved before any date-derived name is handed out.
"""

from __future__ import annotations

import re
from pathlib import Path

_TIMESTAMP_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})_\d{6}$")


def derive_name(stem: str) -> str:
    """Map a note filename stem to its output base name."""
    match = _TIMESTAMP_RE.match(stem)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    return stem


def plan_output_names(
    entries: list[tuple[Path, Path]],
) -> list[tuple[Path, Path, str]]:
    """Give each ``(note_path, out_dir)`` a name no other note in that folder uses.

    Runs in two passes. Pass one reserves the stems you chose on the device.
    Pass two hands out date-derived names around them. Nothing reads the disk,
    and the result depends only on input order, so a rerun produces the same
    names.
    """
    entries = [(Path(note_path), Path(out_dir)) for note_path, out_dir in entries]
    taken: dict[str, set[str]] = {}
    names: dict[int, str] = {}

    def allocate(out_dir: str, base: str) -> str:
        used = taken.setdefault(out_dir, set())
        name = base
        occurrence = 1
        while name in used:
            occurrence += 1
            name = f"{base}-{occurrence}"
        used.add(name)
        return name

    for index, (note_path, out_dir) in enumerate(entries):
        stem = note_path.stem
        if derive_name(stem) == stem:  # you renamed it, so the name is yours
            names[index] = allocate(str(out_dir), stem)
    for index, (note_path, out_dir) in enumerate(entries):
        if index not in names:
            names[index] = allocate(str(out_dir), derive_name(note_path.stem))

    return [
        (note_path, out_dir, names[index]) for index, (note_path, out_dir) in enumerate(entries)
    ]
