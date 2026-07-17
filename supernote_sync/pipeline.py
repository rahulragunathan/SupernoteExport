"""Orchestrate discovery → convert → transcribe → write for a batch of notes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import convert
from .convert import DEFAULT_MAX_PIXELS
from .discover import discover_notes
from .naming import plan_output_names
from .transcribe import Transcriber
from .writer import build_markdown, write_note_outputs


@dataclass
class Summary:
    """Outcome of a batch run."""

    converted: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    failed: list[tuple[Path, str]] = field(default_factory=list)


def run(
    input_path: Path | str,
    output_root: Path | str,
    *,
    transcriber: Transcriber | None = None,
    pdf_mode: str = "raster",
    max_pixels: int = DEFAULT_MAX_PIXELS,
    overwrite: bool = False,
) -> Summary:
    """Convert every note under ``input_path`` into ``output_root``.

    Notes whose ``.md`` already exists are skipped unless ``overwrite``. A single
    failing note is recorded and the batch continues. Transcription runs only when
    a ``transcriber`` is supplied.
    """
    output_root = Path(output_root)
    vectorize = pdf_mode == "vector"

    notes = discover_notes(input_path)
    planned = plan_output_names([(note, output_root / subdir) for note, subdir in notes])

    summary = Summary()
    for note_path, out_dir, name in planned:
        md_path = out_dir / f"{name}.md"
        try:
            if md_path.exists() and not overwrite:
                summary.skipped.append(md_path)
                continue

            pdf_bytes = convert.note_to_pdf(note_path, vectorize=vectorize)

            transcription = ""
            if transcriber is not None:
                images = convert.note_to_page_images(note_path, max_pixels=max_pixels)
                transcription = transcriber.transcribe_pages(images)

            markdown = build_markdown(transcription, f"{name}.pdf")
            write_note_outputs(out_dir, name, pdf_bytes, markdown)
            summary.converted.append(md_path)
        except Exception as error:  # noqa: BLE001 — one bad note must not abort the batch
            summary.failed.append((note_path, repr(error)))
    return summary
