from PIL import Image

from supernote_export.convert import _downscale_to_max_pixels


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
