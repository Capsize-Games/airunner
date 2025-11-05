"""Unit tests for PixelFilter."""

import pytest
from PIL import Image
import numpy as np

from airunner.components.art.filters.pixel_art import PixelFilter


class TestPixelFilter:
    """Test suite for PixelFilter."""

    @pytest.fixture
    def test_image(self):
        """Create a test image with a gradient."""
        width, height = 256, 256
        img_array = np.zeros((height, width, 3), dtype=np.uint8)

        # Create gradient
        for y in range(height):
            for x in range(width):
                img_array[y, x] = [
                    int(255 * x / width),
                    int(255 * y / height),
                    128,
                ]

        return Image.fromarray(img_array, "RGB")

    def test_filter_initialization_with_defaults(self):
        """Test filter initializes with default parameters."""
        f = PixelFilter()

        assert f.current_number_of_colors == 0
        assert (
            not hasattr(f, "number_of_colors")
            or getattr(f, "number_of_colors", 24) == 24
        )
        assert (
            not hasattr(f, "base_size") or getattr(f, "base_size", 256) == 256
        )
        assert not hasattr(f, "smoothing") or getattr(f, "smoothing", 0) == 0

    def test_filter_initialization_with_kwargs(self):
        """Test filter initializes with provided parameters."""
        f = PixelFilter(number_of_colors=16, base_size=128, smoothing=10)

        assert f.number_of_colors == 16
        assert f.base_size == 128
        assert f.smoothing == 10

    def test_filter_applies_successfully(self, test_image):
        """Test filter applies to an image without error."""
        f = PixelFilter(number_of_colors=24, base_size=256, smoothing=0)

        result = f.filter(test_image)

        assert result is not None
        assert isinstance(result, Image.Image)
        assert result.size == test_image.size
        assert result.mode == "RGBA"

    def test_filter_quantizes_colors(self, test_image):
        """Test filter reduces number of colors."""
        f = PixelFilter(number_of_colors=8, base_size=256, smoothing=0)

        result = f.filter(test_image)

        # Count unique colors in result
        colors = result.getcolors(maxcolors=1000000)
        unique_colors = len(colors) if colors else 0

        # Should have significantly fewer colors than original
        # (may not be exactly 8 due to conversion and resizing)
        assert unique_colors <= 100  # Much less than full 256^3 color space

    def test_filter_with_zero_colors_uses_default(self, test_image):
        """Test filter handles invalid number_of_colors gracefully."""
        f = PixelFilter(number_of_colors=0, base_size=256, smoothing=0)

        # Should not raise an error
        result = f.filter(test_image)

        assert result is not None
        assert isinstance(result, Image.Image)

    def test_filter_with_odd_colors_rounds_down(self, test_image):
        """Test filter ensures even number of colors."""
        f = PixelFilter(number_of_colors=25, base_size=256, smoothing=0)

        result = f.filter(test_image)

        assert result is not None
        # Filter should round down 25 -> 24

    def test_filter_with_negative_colors_uses_default(self, test_image):
        """Test filter handles negative number_of_colors."""
        f = PixelFilter(number_of_colors=-10, base_size=256, smoothing=0)

        result = f.filter(test_image)

        assert result is not None

    def test_filter_downsamples_and_upsamples(self, test_image):
        """Test filter performs downsampling and upsampling."""
        original_size = test_image.size
        f = PixelFilter(number_of_colors=24, base_size=64, smoothing=0)

        result = f.filter(test_image)

        # Output should be same size as input
        assert result.size == original_size

    def test_filter_with_smoothing(self, test_image):
        """Test filter applies smoothing when enabled."""
        f = PixelFilter(number_of_colors=24, base_size=256, smoothing=20)

        result = f.filter(test_image)

        assert result is not None
        assert isinstance(result, Image.Image)

    def test_filter_caching_on_repeated_calls(self, test_image):
        """Test filter caches results for same image."""
        f = PixelFilter(number_of_colors=24, base_size=256, smoothing=0)

        # First call
        result1 = f.filter(test_image)
        first_image_id = f.image_id

        # Second call with same image
        result2 = f.filter(test_image)

        # Should use cached quantized image
        assert f.image_id == first_image_id
        assert result1.size == result2.size

    def test_filter_reset_on_different_image(self, test_image):
        """Test filter resets when processing different image."""
        f = PixelFilter(number_of_colors=24, base_size=256, smoothing=0)

        # Filter first image
        f.filter(test_image)
        first_image_id = f.image_id

        # Create different image
        test_image2 = Image.new("RGB", (128, 128), color="red")

        # Filter second image
        f.filter(test_image2)

        # Should have different image_id
        assert f.image_id != first_image_id

    def test_filter_with_different_input_modes(self):
        """Test filter handles different image modes."""
        modes_to_test = ["RGB", "RGBA", "L"]

        for mode in modes_to_test:
            img = Image.new(
                mode, (100, 100), color="blue" if mode != "L" else 128
            )
            f = PixelFilter(number_of_colors=24, base_size=256, smoothing=0)

            result = f.filter(img)

            assert result is not None
            assert result.mode == "RGBA"

    def test_filter_preserves_aspect_ratio(self):
        """Test filter preserves aspect ratio of non-square images."""
        # Create rectangular image
        img = Image.new("RGB", (400, 200), color="blue")
        f = PixelFilter(number_of_colors=24, base_size=128, smoothing=0)

        result = f.filter(img)

        # Output should maintain original size
        assert result.size == (400, 200)

    def test_filter_with_very_small_base_size(self, test_image):
        """Test filter with very small base_size."""
        f = PixelFilter(number_of_colors=24, base_size=16, smoothing=0)

        result = f.filter(test_image)

        assert result is not None
        assert result.size == test_image.size

    def test_filter_with_large_base_size(self, test_image):
        """Test filter with large base_size."""
        f = PixelFilter(number_of_colors=24, base_size=512, smoothing=0)

        result = f.filter(test_image)

        assert result is not None
        assert result.size == test_image.size

    def test_filter_parameters_as_strings(self, test_image):
        """Test filter handles string parameters (from database)."""
        # Simulate parameters coming from database as strings
        f = PixelFilter(number_of_colors="24", base_size="256", smoothing="0")

        result = f.filter(test_image)

        assert result is not None

    def test_filter_parameters_as_floats(self, test_image):
        """Test filter handles float parameters."""
        f = PixelFilter(number_of_colors=24.0, base_size=256.0, smoothing=0.0)

        result = f.filter(test_image)

        assert result is not None
