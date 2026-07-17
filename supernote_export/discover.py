"""Resolve a CLI ``--input`` (file or folder) into notes to convert."""

from __future__ import annotations

from pathlib import Path

NOTE_SUFFIX = ".note"


def discover_notes(input_path: Path | str) -> list[tuple[Path, Path]]:
    """Return sorted ``(note_path, relative_subdir)`` pairs.

    ``relative_subdir`` is the note's parent directory relative to the input
    root (``Path(".")`` for a single file or a note sitting directly in the
    input folder). Callers join it onto the output root to mirror the tree.
    """
    input_path = Path(input_path)

    if input_path.is_file():
        if input_path.suffix != NOTE_SUFFIX:
            raise ValueError(f"Not a .note file: {input_path}")
        return [(input_path, Path("."))]

    if input_path.is_dir():
        notes = sorted(input_path.rglob(f"*{NOTE_SUFFIX}"))
        return [(note, note.parent.relative_to(input_path)) for note in notes]

    raise FileNotFoundError(input_path)
