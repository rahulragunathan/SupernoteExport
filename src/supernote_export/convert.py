"""Turn a ``.note`` into a PDF and per-page images, using ``supernotelib``.

The PDF is the archival file embedded in the Markdown. The page images are what
the transcriber reads. Supernote pages are bitmaps on the device, so the default
raster PDF reproduces them pixel for pixel. ``vectorize=True`` traces them into
scalable paths instead.
"""

from __future__ import annotations

import math
from pathlib import Path

import supernotelib as sn
from PIL import Image
from supernotelib import converter

ALL_PAGES = -1

# A Supernote page renders at 1920x2560, about 4.9M pixels. Above roughly 2M, the
# Qwen3-VL vision stack sometimes returns an *empty* generation, so pages are shrunk
# well below that line before the model sees them. Shrinking here rather than in the
# transcriber keeps the cap model-agnostic: every model gets an already-safe image.
#
# 1.5M is a hard-coded conservative number, not read from model metadata, and that is
# deliberate. The cliff is undocumented and sits below every capacity the model
# advertises. Measured on a failing page: reliable at or below 1.77M, empty at or
# above 2.0M. The model's config declares 16.7M, and its num_position_embeddings math
# implies about 2.36M; both return empty output. See ROADMAP.md. Do not raise this
# near 2M — tune other models with ``--max-pixels``.
DEFAULT_MAX_PIXELS = 1_500_000


def _load(note_path: Path | str) -> sn.Notebook:
    return sn.load_notebook(str(note_path))


def _downscale_to_max_pixels(image: Image.Image, max_pixels: int) -> Image.Image:
    """Shrink ``image`` to at most ``max_pixels``, keeping its aspect ratio."""
    pixels = image.width * image.height
    if max_pixels <= 0 or pixels <= max_pixels:
        return image
    factor = math.sqrt(max_pixels / pixels)
    # Floor, not round, so the result always stays inside the cap.
    new_size = (max(1, int(image.width * factor)), max(1, int(image.height * factor)))
    return image.resize(new_size, Image.LANCZOS)


def note_to_pdf(note_path: Path | str, vectorize: bool = False) -> bytes:
    """Render the whole note to a single PDF, raster by default."""
    notebook = _load(note_path)
    return converter.PdfConverter(notebook).convert(ALL_PAGES, vectorize=vectorize)


def note_to_page_images(
    note_path: Path | str, max_pixels: int = DEFAULT_MAX_PIXELS
) -> list[Image.Image]:
    """Render each page to a PIL image for the transcriber.

    Pages are shrunk to at most ``max_pixels``, which the model needs to transcribe
    reliably — see ``DEFAULT_MAX_PIXELS``. This does not touch the archival PDF,
    which is rendered separately from the full-resolution note.
    """
    notebook = _load(note_path)
    image_converter = converter.ImageConverter(notebook)
    images: list[Image.Image] = []
    for page_number in range(notebook.get_total_pages()):
        image = image_converter.convert(page_number)
        images.append(_downscale_to_max_pixels(image, max_pixels))
    return images
