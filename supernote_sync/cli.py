"""Command-line entrypoint: ``python -m supernote_sync``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .convert import DEFAULT_MAX_PIXELS
from .pipeline import Summary, run
from .transcribe import DEFAULT_MODEL


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="supernote_sync",
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
        "--page-separators",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Insert a '---' rule between pages in the transcription (default: off, "
        "just a blank line). Use --page-separators to add the rule.",
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

        transcriber = MlxVlmTranscriber(model=args.model, page_separators=args.page_separators)

    summary = run(
        args.input,
        args.output,
        transcriber=transcriber,
        pdf_mode=args.pdf_mode,
        max_pixels=args.max_pixels,
        overwrite=args.overwrite,
    )
    _print_summary(summary)
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
