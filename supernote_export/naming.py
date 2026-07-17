"""Output-name derivation for converted notes.

Supernote names files by capture timestamp (``YYYYMMDD_HHMMSS``); when the user
renames a note on-device the stem is arbitrary. We turn a timestamp stem into a
clean ``YYYY-MM-DD`` date and keep any other stem verbatim. Distinct notes that
map to the same name inside the same output directory get a deterministic
``-2``/``-3`` suffix based on input order.
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
    """Assign a collision-free base name to each ``(note_path, out_dir)``.

    Disambiguation is scoped per output directory and depends only on input
    order (callers pass a stably sorted list), so runs are reproducible.
    """
    counts: dict[tuple[str, str], int] = {}
    planned: list[tuple[Path, Path, str]] = []
    for note_path, out_dir in entries:
        base = derive_name(Path(note_path).stem)
        key = (str(out_dir), base)
        counts[key] = counts.get(key, 0) + 1
        occurrence = counts[key]
        name = base if occurrence == 1 else f"{base}-{occurrence}"
        planned.append((Path(note_path), Path(out_dir), name))
    return planned
