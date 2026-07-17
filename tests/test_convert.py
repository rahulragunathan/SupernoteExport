from pathlib import Path

from PIL import Image

from supernote_export.convert import (
    DEFAULT_MAX_PIXELS,
    _downscale_to_max_pixels,
    note_to_page_images,
)

SAMPLE_NOTE = Path(__file__).parent / "fixtures" / "20260717_012708.note"
SAMPLE_PAGES = 3


def test_downscale_shrinks_oversized_image_under_cap():
    image = Image.new("RGB", (1920, 2560))  # 4.92M px
    out = _downscale_to_max_pixels(image, 1_500_000)
    assert out.width * out.height <= 1_500_000


def test_downscale_preserves_aspect_ratio():
    image = Image.new("RGB", (1920, 2560))
    out = _downscale_to_max_pixels(image, 1_500_000)
    assert abs(out.width / out.height - 1920 / 2560) < 0.01


def test_downscale_leaves_small_image_untouched():
    image = Image.new("RGB", (800, 600))  # 0.48M px
    out = _downscale_to_max_pixels(image, 1_500_000)
    assert out.size == (800, 600)


def test_downscale_disabled_when_cap_nonpositive():
    image = Image.new("RGB", (1920, 2560))
    assert _downscale_to_max_pixels(image, 0).size == (1920, 2560)


def test_note_to_page_images_caps_pages_to_max_pixels():
    """Regression guard for the empty-generation cliff: every page handed to the VLM
    must be at or under the cap. This is the layer-level assertion that a silent
    resolution regression would trip — caught here rather than as an empty .md."""
    images = note_to_page_images(SAMPLE_NOTE, max_pixels=DEFAULT_MAX_PIXELS)
    assert len(images) == SAMPLE_PAGES
    assert all(im.width * im.height <= DEFAULT_MAX_PIXELS for im in images)
