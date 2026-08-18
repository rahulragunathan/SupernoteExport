"""Build and write the per-note Obsidian outputs (Markdown + PDF)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def build_markdown(transcription: str, pdf_filename: str) -> str:
    """Compose the note body: transcription first, PDF embed at the bottom.

    When there is no transcription (``--no-transcribe``), the body is just the
    Obsidian embed.
    """
    embed = f"![[{pdf_filename}]]\n"
    body = transcription.rstrip() if transcription else ""
    if not body:
        return embed
    return f"{body}\n\n{embed}"


def _stage(path: Path, data: bytes) -> Path:
    """Write ``data`` to a uniquely named temp file beside ``path``.

    The name is unique rather than a fixed ``.<name>.tmp`` so that two runs over
    the same output folder cannot write to, or clean up, each other's file.
    """
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return tmp


def write_note_outputs(
    out_dir: Path,
    name: str,
    pdf_bytes: bytes,
    markdown: str,
) -> tuple[Path, Path]:
    """Write ``<name>.pdf`` and ``<name>.md`` into ``out_dir`` (created if needed).

    Both files are staged first, then renamed into place, so a final path never
    holds a half-written file — ``pipeline.run`` reads a file's presence as proof
    the note was converted. This promises only that no reader sees a partial
    file. It is not a durability promise, and the two renames are not one
    transaction.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"{name}.pdf"
    md_path = out_dir / f"{name}.md"

    staged: list[tuple[Path, Path]] = []
    try:
        # Encoding and disk writes happen here, while both final paths are still
        # untouched. The renames then follow together.
        staged.append((_stage(pdf_path, pdf_bytes), pdf_path))
        staged.append((_stage(md_path, markdown.encode("utf-8")), md_path))
        for tmp, final in staged:
            os.replace(tmp, final)
    finally:
        for tmp, _ in staged:
            tmp.unlink(missing_ok=True)  # already gone once renamed
    return pdf_path, md_path
