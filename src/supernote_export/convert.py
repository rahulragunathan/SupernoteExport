"""Convert a ``.note`` into a PDF and per-page images via ``supernotelib``.

The PDF is the archival artifact embedded in the Markdown; the per-page images
are what the VLM transcriber reads. Supernote pages are bitmaps on-device, so
the default (raster) PDF is a pixel-exact reproduction; ``vectorize=True`` traces
them into scalable vector paths instead.
"""

from __future__ import annotations

import math
from pathlib import Path

import supernotelib as sn
from PIL import Image
from supernotelib import converter

ALL_PAGES = -1

# Native Supernote pages render at ~4.9M pixels (1920x2560). Above ~2M pixels the
# Qwen3-VL vision stack intermittently collapses to an *empty* generation, so page
# images are downscaled well below that boundary before reaching the model. This is a
# model-agnostic pre-render cap (any VLM receives an already-safe image), independent
# of the model's own processor internals.
#
# The default (1.5M) is a *hard-coded conservative constant*, not derived from model
# metadata — and deliberately so: the cliff is an undocumented quirk whose safe point
# sits BELOW everything the model advertises. Measured on a failing page: reliable
# ≤1.77M px, empty ≥2.0M px (the model's config declares 16.7M, and its
# num_position_embeddings math implies ~2.36M — both produce empty output). See
# ROADMAP.md. Do not raise the default near 2M; other models are tuned via
# ``--max-pixels``.
DEFAULT_MAX_PIXELS = 1_500_000


def _load(note_path: Path | str) -> sn.Notebook:
    return sn.load_notebook(str(note_path))


def _downscale_to_max_pixels(image: Image.Image, max_pixels: int) -> Image.Image:
    """Shrink ``image`` (preserving aspect ratio) so it holds at most ``max_pixels``."""
    pixels = image.width * image.height
    if max_pixels <= 0 or pixels <= max_pixels:
        return image
    factor = math.sqrt(max_pixels / pixels)
    # Floor (not round) so the result is guaranteed to stay within the cap.
    new_size = (max(1, int(image.width * factor)), max(1, int(image.height * factor)))
    return image.resize(new_size, Image.LANCZOS)


def note_to_pdf(note_path: Path | str, vectorize: bool = False) -> bytes:
    """Render the whole note to a single PDF (raster by default)."""
    notebook = _load(note_path)
    return converter.PdfConverter(notebook).convert(ALL_PAGES, vectorize=vectorize)


def note_to_page_images(
    note_path: Path | str, max_pixels: int = DEFAULT_MAX_PIXELS
) -> list[Image.Image]:
    """Render each page to a PIL image for the transcriber.

    Pages are downscaled to at most ``max_pixels`` — essential for reliable VLM
    transcription (see ``DEFAULT_MAX_PIXELS``). The archival PDF is unaffected;
    it is rendered separately from the full-resolution note.
    """
    notebook = _load(note_path)
    image_converter = converter.ImageConverter(notebook)
    images: list[Image.Image] = []
    for page_number in range(notebook.get_total_pages()):
        image = image_converter.convert(page_number)
        images.append(_downscale_to_max_pixels(image, max_pixels))
    return images
