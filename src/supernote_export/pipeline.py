"""Orchestrate discovery → convert → transcribe → write for a batch of notes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from . import convert
from .convert import DEFAULT_MAX_PIXELS
from .discover import discover_notes
from .naming import plan_output_names
from .transcribe import Transcriber
from .writer import build_markdown, write_note_outputs

# Called once per note as the batch progresses: (index, total, note_path, status),
# where status is "convert" (before the slow work) or "skip" (output already exists).
ProgressCallback = Callable[[int, int, Path, str], None]


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
    on_progress: ProgressCallback | None = None,
) -> Summary:
    """Convert every note under ``input_path`` into ``output_root``.

    Notes whose ``.md`` already exists are skipped unless ``overwrite``. A single
    failing note is recorded and the batch continues. Transcription runs only when
    a ``transcriber`` is supplied. ``on_progress``, if given, is called once per note
    (see ``ProgressCallback``) — before the slow conversion, so a caller can show a
    live per-note line during long batches.
    """
    output_root = Path(output_root)
    vectorize = pdf_mode == "vector"

    notes = discover_notes(input_path)
    planned = plan_output_names([(note, output_root / subdir) for note, subdir in notes])
    total = len(planned)

    summary = Summary()
    for index, (note_path, out_dir, name) in enumerate(planned, start=1):
        md_path = out_dir / f"{name}.md"
        try:
            if md_path.exists() and not overwrite:
                if on_progress is not None:
                    on_progress(index, total, note_path, "skip")
                summary.skipped.append(md_path)
                continue

            if on_progress is not None:
                on_progress(index, total, note_path, "convert")

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
