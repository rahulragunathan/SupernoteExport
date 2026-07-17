"""Command-line entrypoint: ``python -m supernote_export``."""

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
        help="A single .note file or a folder of them (searched recursively).",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output folder; the input's subfolder tree is mirrored under it.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"MLX-VLM model for transcription (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--pdf-mode",
        choices=("raster", "vector"),
        default="raster",
        help="Embedded PDF rendering: raster (pixel-exact, default) or vector (traced).",
    )
    parser.add_argument(
        "--max-pixels",
        type=int,
        default=DEFAULT_MAX_PIXELS,
        help="Cap on the page-image pixels fed to the VLM (default: "
        f"{DEFAULT_MAX_PIXELS:,}). Native ~4.9M reliably breaks Qwen3-VL; keep this "
        "well under ~2M.",
    )
    parser.add_argument(
        "--page-markers",
        choices=PAGE_MARKER_CHOICES,
        default="none",
        help="How to separate pages in the transcription: 'none' (blank line, "
        "default), 'line-break' ('---' rule), or 'page-numbers' ('## Page N' "
        "headers, addressable and aligned to the PDF's page numbers).",
    )
    parser.add_argument(
        "--no-transcribe",
        action="store_true",
        help="Only produce PDFs (skip the VLM); the .md holds just the embed.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-convert notes even if their .md already exists (default: skip).",
    )
    return parser


def _print_progress(current: int, total: int, note_path: Path, status: str) -> None:
    """Emit one per-note progress line to stderr as the batch runs."""
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
        # Imported lazily so --no-transcribe runs never load MLX.
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
