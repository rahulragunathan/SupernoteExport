"""Command-line entry point: ``python -m supernote_export``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .convert import DEFAULT_MAX_PIXELS
from .pipeline import Summary, run
from .transcribe import DEFAULT_MODEL, PAGE_MARKER_CHOICES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="supernote_export",
        description="Convert Supernote .note files into Obsidian-ready PDFs and "
        "locally-transcribed Markdown.",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="A single .note file, or a folder of them searched recursively.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output folder. The input's subfolder tree is mirrored under it.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"MLX-VLM model used for transcription (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--pdf-mode",
        choices=("raster", "vector"),
        default="raster",
        help="Embedded PDF: raster is pixel-exact (default), vector traces the strokes.",
    )
    parser.add_argument(
        "--max-pixels",
        type=int,
        default=DEFAULT_MAX_PIXELS,
        help="Cap on the page images sent to the model (default: "
        f"{DEFAULT_MAX_PIXELS:,}). A full page is about 4.9M pixels, which reliably "
        "breaks Qwen3-VL, so keep this well under 2M.",
    )
    parser.add_argument(
        "--page-markers",
        choices=PAGE_MARKER_CHOICES,
        default="none",
        help="How pages are separated in the transcription: 'none' is a blank line "
        "(default), 'line-break' is a '---' rule, and 'page-numbers' adds "
        "'## Page N' headings that match the PDF's page numbers.",
    )
    parser.add_argument(
        "--no-transcribe",
        action="store_true",
        help="Produce PDFs only, skipping the model. The .md holds just the embed.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Convert a note again even when its outputs exist. By default a note is "
        "skipped once both its .md and .pdf are there.",
    )
    return parser


def _print_progress(current: int, total: int, note_path: Path, status: str) -> None:
    """Print one line per note to stderr as the batch runs."""
    verb = "Skipping" if status == "skip" else "Converting"
    suffix = " (exists)" if status == "skip" else ""
    print(f"[{current}/{total}] {verb} {note_path.name}{suffix}", file=sys.stderr)


def _print_summary(summary: Summary) -> None:
    print(
        f"\nDone: {len(summary.converted)} converted, "
        f"{len(summary.skipped)} skipped, {len(summary.failed)} failed."
    )
    for note_path, error in summary.failed:
        print(f"  FAILED {note_path}: {error}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    transcriber = None
    if not args.no_transcribe:
        # Imported here so a --no-transcribe run never loads MLX.
        from .transcribe import MlxVlmTranscriber

        transcriber = MlxVlmTranscriber(model=args.model, page_markers=args.page_markers)

    summary = run(
        args.input,
        args.output,
        transcriber=transcriber,
        pdf_mode=args.pdf_mode,
        max_pixels=args.max_pixels,
        overwrite=args.overwrite,
        on_progress=_print_progress,
    )
    _print_summary(summary)
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
