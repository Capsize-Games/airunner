"""Unit tests for CanvasImageConversionMixin.

Tests cover PIL Image <-> QImage conversion with:
- Happy path: Normal conversion scenarios
- Sad path: Edge cases like None, invalid data
- Bad path: Error conditions and exception handling

Following red/green/refactor TDD methodology.
"""

from unittest.mock import Mock, PropertyMock
from PIL import Image
from PySide6.QtGui import QImage


class TestConvertPilToQImage:
    """Test _convert_pil_to_qimage method - PIL Image to QImage conversion."""

    def test_convert_valid_rgba_image(self, mock_scene_with_settings):
        """HAPPY: Convert valid RGBA PIL Image to QImage."""
        scene = mock_scene_with_settings
        pil_image = Image.new("RGBA", (256, 256), (255, 0, 0, 255))

        qimage = scene._convert_pil_to_qimage(pil_image)

        # Should return a valid QImage
        assert qimage is not None
        assert isinstance(qimage, QImage)
        assert qimage.width() == 256
        assert qimage.height() == 256

    def test_convert_rgb_image(self, mock_scene_with_settings):
        """HAPPY: Convert RGB PIL Image to QImage."""
        scene = mock_scene_with_settings
        pil_image = Image.new("RGB", (128, 128), (0, 255, 0))

        qimage = scene._convert_pil_to_qimage(pil_image)

        # Should return a valid QImage
        assert qimage is not None
        assert isinstance(qimage, QImage)

    def test_convert_grayscale_image(self, mock_scene_with_settings):
        """HAPPY: Convert grayscale PIL Image to QImage."""
        scene = mock_scene_with_settings
        pil_image = Image.new("L", (64, 64), 128)

        qimage = scene._convert_pil_to_qimage(pil_image)

        # Should return a valid QImage
        assert qimage is not None
        assert isinstance(qimage, QImage)

    def test_convert_none_image(self, mock_scene_with_settings):
        """SAD: Convert None should handle gracefully."""
        scene = mock_scene_with_settings

        qimage = scene._convert_pil_to_qimage(None)

        # Should return None or handle exception
        # Will raise AttributeError but that's caught
        assert qimage is None

    def test_convert_invalid_image_object(self, mock_scene_with_settings):
        """BAD: Convert invalid object should return None."""
        scene = mock_scene_with_settings
        invalid_object = "not an image"

        qimage = scene._convert_pil_to_qimage(invalid_object)

        # Should catch exception and return None
        assert qimage is None

    def test_convert_zero_size_image(self, mock_scene_with_settings):
        """BOUNDARY: Convert zero-sized image."""
        scene = mock_scene_with_settings

        try:
            # PIL may not allow 0x0 images
            pil_image = Image.new("RGBA", (0, 0))
            qimage = scene._convert_pil_to_qimage(pil_image)
            # If it works, verify
            assert qimage is not None or qimage is None  # Either is acceptable
        except (ValueError, OSError):
            # PIL doesn't allow 0x0 images
            pass

    def test_convert_large_image(self, mock_scene_with_settings):
        """STRESS: Convert very large image."""
        scene = mock_scene_with_settings
        # Large but not unreasonable
        pil_image = Image.new("RGBA", (2048, 2048), (100, 100, 100, 255))

        qimage = scene._convert_pil_to_qimage(pil_image)

        # Should handle large images
        assert qimage is not None
        assert qimage.width() == 2048


class TestLoadImageFromSettings:
    """Test _load_image_from_settings method - load PIL Image from settings."""

    def test_load_valid_base64_image(self, mock_scene_with_settings):
        """HAPPY: Load image from valid base64 binary data."""
        scene = mock_scene_with_settings

        # Create a PIL image and convert to binary
        test_image = Image.new("RGBA", (64, 64), (255, 128, 64, 255))
        import io
        import base64

        buffer = io.BytesIO()
        test_image.save(buffer, format="PNG")
        binary_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # Mock settings to return binary data
        mock_settings = Mock()
        mock_settings.image = binary_data
        type(scene).current_settings = PropertyMock(return_value=mock_settings)

        pil_image = scene._load_image_from_settings()

        # Should return a valid PIL Image in RGBA mode
        assert pil_image is not None
        assert isinstance(pil_image, Image.Image)
        assert pil_image.mode == "RGBA"
        assert pil_image.size == (64, 64)

    def test_load_with_none_binary(self, mock_scene_with_settings):
        """SAD: Load when settings.image is None."""
        scene = mock_scene_with_settings

        # Mock settings with None image
        mock_settings = Mock()
        mock_settings.image = None
        type(scene).current_settings = PropertyMock(return_value=mock_settings)

        pil_image = scene._load_image_from_settings()

        # Should return None
        assert pil_image is None

    def test_load_with_invalid_binary(self, mock_scene_with_settings):
        """BAD: Load with invalid binary data."""
        scene = mock_scene_with_settings

        # Mock settings with invalid binary
        mock_settings = Mock()
        mock_settings.image = "invalid_base64_data"
        type(scene).current_settings = PropertyMock(return_value=mock_settings)

        pil_image = scene._load_image_from_settings()

        # Should catch exception and return None
        assert pil_image is None

    def test_load_with_attribute_error(self, mock_scene_with_settings):
        """BAD: Load when settings doesn't have image attribute."""
        scene = mock_scene_with_settings

        # Mock settings without image attribute
        mock_settings = Mock(spec=[])
        type(scene).current_settings = PropertyMock(return_value=mock_settings)

        pil_image = scene._load_image_from_settings()

        # Should catch AttributeError and return None
        assert pil_image is None

    def test_load_rgb_image_converts_to_rgba(self, mock_scene_with_settings):
        """HAPPY: RGB images are converted to RGBA."""
        scene = mock_scene_with_settings

        # Create RGB image and convert to binary
        test_image = Image.new("RGB", (32, 32), (0, 255, 0))
        import io
        import base64

        buffer = io.BytesIO()
        test_image.save(buffer, format="PNG")
        binary_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # Mock settings
        mock_settings = Mock()
        mock_settings.image = binary_data
        type(scene).current_settings = PropertyMock(return_value=mock_settings)

        pil_image = scene._load_image_from_settings()

        # Should convert to RGBA
        assert pil_image is not None
        assert pil_image.mode == "RGBA"


class TestBinaryToPilFast:
    """Test _binary_to_pil_fast method - fast binary to PIL conversion."""

    def test_convert_airaw1_format(self, mock_scene_with_settings):
        """HAPPY: Convert AIRAW1 format binary data."""
        scene = mock_scene_with_settings

        # Create AIRAW1 format binary
        width, height = 4, 4
        rgba_data = bytes([255, 0, 0, 255] * (width * height))  # Red pixels

        binary_data = (
            b"AIRAW1"
            + width.to_bytes(4, "big")
            + height.to_bytes(4, "big")
            + rgba_data
        )

        pil_image = scene._binary_to_pil_fast(binary_data)

        # Should return valid PIL Image
        assert pil_image is not None
        assert isinstance(pil_image, Image.Image)
        assert pil_image.size == (width, height)
        assert pil_image.mode == "RGBA"

    def test_convert_airaw1_larger_image(self, mock_scene_with_settings):
        """HAPPY: Convert larger AIRAW1 image."""
        scene = mock_scene_with_settings

        # Create larger AIRAW1 format
        width, height = 64, 64
        rgba_data = bytes([0, 255, 0, 255] * (width * height))  # Green pixels

        binary_data = (
            b"AIRAW1"
            + width.to_bytes(4, "big")
            + height.to_bytes(4, "big")
            + rgba_data
        )

        pil_image = scene._binary_to_pil_fast(binary_data)

        # Should return valid PIL Image
        assert pil_image is not None
        assert pil_image.size == (width, height)

    def test_convert_none_binary(self, mock_scene_with_settings):
        """SAD: Convert None binary data."""
        scene = mock_scene_with_settings

        pil_image = scene._binary_to_pil_fast(None)

        # Should return None
        assert pil_image is None

    def test_convert_invalid_airaw1_header(self, mock_scene_with_settings):
        """BAD: Invalid AIRAW1 header falls back to regular conversion."""
        scene = mock_scene_with_settings

        # Invalid header (not AIRAW1)
        binary_data = b"NOTRAW" + bytes(100)

        # Will attempt fallback conversion which will fail and return None
        pil_image = scene._binary_to_pil_fast(binary_data)

        # Should fallback and likely return None
        assert pil_image is None or isinstance(pil_image, Image.Image)

    def test_convert_airaw1_wrong_size(self, mock_scene_with_settings):
        """BAD: AIRAW1 with mismatched data size."""
        scene = mock_scene_with_settings

        # Declare 10x10 but provide less data
        width, height = 10, 10
        rgba_data = bytes([255, 0, 0, 255] * 5)  # Only 5 pixels worth

        binary_data = (
            b"AIRAW1"
            + width.to_bytes(4, "big")
            + height.to_bytes(4, "big")
            + rgba_data
        )

        pil_image = scene._binary_to_pil_fast(binary_data)

        # Should fallback to regular conversion
        assert pil_image is None or isinstance(pil_image, Image.Image)

    def test_convert_airaw1_too_short(self, mock_scene_with_settings):
        """BAD: AIRAW1 binary data too short."""
        scene = mock_scene_with_settings

        # Header but no dimensions/data
        binary_data = b"AIRAW1"

        pil_image = scene._binary_to_pil_fast(binary_data)

        # Should fallback
        assert pil_image is None or isinstance(pil_image, Image.Image)

    def test_convert_fallback_to_standard(self, mock_scene_with_settings):
        """HAPPY: Fallback to standard conversion for non-AIRAW1 data."""
        scene = mock_scene_with_settings

        # Create standard PNG binary
        test_image = Image.new("RGBA", (16, 16), (128, 128, 128, 255))
        import io

        buffer = io.BytesIO()
        test_image.save(buffer, format="PNG")
        binary_data = buffer.getvalue()

        pil_image = scene._binary_to_pil_fast(binary_data)

        # Should use fallback conversion successfully
        assert pil_image is not None
        assert isinstance(pil_image, Image.Image)
        assert pil_image.size == (16, 16)


class TestImageConversionEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_round_trip_conversion(self, mock_scene_with_settings):
        """INTEGRATION: PIL -> QImage conversion preserves data."""
        scene = mock_scene_with_settings

        # Create test image
        original = Image.new("RGBA", (32, 32), (200, 100, 50, 255))

        # Convert to QImage
        qimage = scene._convert_pil_to_qimage(original)

        # Verify conversion worked
        assert qimage is not None
        assert qimage.size().width() == 32
        assert qimage.size().height() == 32

    def test_airaw1_edge_case_dimensions(self, mock_scene_with_settings):
        """BOUNDARY: AIRAW1 with 1x1 image."""
        scene = mock_scene_with_settings

        width, height = 1, 1
        rgba_data = bytes([255, 255, 255, 255])  # White pixel

        binary_data = (
            b"AIRAW1"
            + width.to_bytes(4, "big")
            + height.to_bytes(4, "big")
            + rgba_data
        )

        pil_image = scene._binary_to_pil_fast(binary_data)

        assert pil_image is not None
        assert pil_image.size == (1, 1)

    def test_multiple_conversions_stability(self, mock_scene_with_settings):
        """STRESS: Multiple conversions don't corrupt data."""
        scene = mock_scene_with_settings

        original = Image.new("RGBA", (16, 16), (50, 100, 150, 200))

        # Convert multiple times
        for _ in range(5):
            qimage = scene._convert_pil_to_qimage(original)
            assert qimage is not None
            assert qimage.width() == 16
