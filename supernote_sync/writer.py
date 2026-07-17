"""Build and write the per-note Obsidian outputs (Markdown + PDF)."""

from __future__ import annotations

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


def write_note_outputs(
    out_dir: Path,
    name: str,
    pdf_bytes: bytes,
    markdown: str,
) -> tuple[Path, Path]:
    """Write ``<name>.pdf`` and ``<name>.md`` into ``out_dir`` (created if needed)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"{name}.pdf"
    md_path = out_dir / f"{name}.md"
    pdf_path.write_bytes(pdf_bytes)
    md_path.write_text(markdown, encoding="utf-8")
    return pdf_path, md_path
