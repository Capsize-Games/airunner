"""Unit tests for CanvasClipboardMixin."""

import unittest
from unittest.mock import MagicMock, patch
from PIL import Image
import io
from PySide6.QtGui import QImage
from PySide6.QtCore import QByteArray
from airunner.components.art.gui.widgets.canvas.mixins.canvas_clipboard_mixin import (
    CanvasClipboardMixin,
)


class MockMimeData:
    """Mock implementation of QMimeData."""

    def __init__(self):
        self._formats = []
        self._data = {}
        self._has_image = False
        self._has_urls = False
        self._urls = []
        self._has_text = False
        self._text = ""
        self._image = None

    def formats(self):
        return self._formats

    def hasImage(self):
        return self._has_image

    def hasUrls(self):
        return self._has_urls

    def hasText(self):
        return self._has_text

    def image(self):
        return self._image

    def urls(self):
        return self._urls

    def text(self):
        return self._text

    def data(self, format_str):
        return self._data.get(format_str, QByteArray())


class TestCanvasClipboardMixin(unittest.TestCase):
    """Test suite for CanvasClipboardMixin."""

    def setUp(self):
        """Set up test fixtures."""
        self.mixin = CanvasClipboardMixin()
        self.mixin.logger = MagicMock()
        self.mixin._resize_image = MagicMock(side_effect=lambda img: img)
        self.mixin._add_image_to_undo = MagicMock()
        self.mixin.initialize_image = MagicMock()
        self.mixin._load_image_from_url_or_file = MagicMock()

    def test_on_paste_image_from_clipboard(self):
        """Test on_paste_image_from_clipboard signal handler."""
        self.mixin.application_settings = MagicMock()
        self.mixin.application_settings.resize_on_paste = True
        self.mixin.current_active_image = None
        self.mixin._commit_layer_history_transaction = MagicMock()

        with patch.object(
            self.mixin, "_paste_image_from_clipboard"
        ) as mock_paste:
            mock_paste.return_value = Image.new("RGBA", (100, 100))
            self.mixin.on_paste_image_from_clipboard()
            mock_paste.assert_called_once()
            self.mixin._resize_image.assert_called_once()
            self.mixin._add_image_to_undo.assert_called_once()
            self.mixin.initialize_image.assert_called_once()

    def test_on_paste_image_from_clipboard_no_image(self):
        """Test on_paste_image_from_clipboard when no image in clipboard."""
        with patch.object(
            self.mixin, "_paste_image_from_clipboard"
        ) as mock_paste:
            mock_paste.return_value = None
            self.mixin.on_paste_image_from_clipboard()
            mock_paste.assert_called_once()
            self.mixin._resize_image.assert_not_called()
            self.mixin._add_image_to_undo.assert_not_called()
            self.mixin.initialize_image.assert_not_called()

    @unittest.skip("Requires real Qt environment - integration test")
    def test_try_qimage_from_clipboard_success(self):
        """Test _try_qimage_from_clipboard with valid QImage."""
        mock_clipboard = MagicMock()
        mock_mime = MockMimeData()
        mock_mime._has_image = True

        # Create a real QImage for testing
        qimg = QImage(100, 100, QImage.Format.Format_RGBA8888)
        qimg.fill(0)
        mock_mime._image = qimg

        mock_clipboard.mimeData.return_value = mock_mime
        mock_clipboard.image.return_value = qimg

        result = self.mixin._try_qimage_from_clipboard(
            mock_mime, mock_clipboard
        )
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.size, (100, 100))
        self.assertEqual(result.mode, "RGBA")

    def test_try_qimage_from_clipboard_no_image(self):
        """Test _try_qimage_from_clipboard when clipboard has no image."""
        mock_clipboard = MagicMock()
        mock_mime = MockMimeData()
        mock_mime._has_image = False

        mock_clipboard.mimeData.return_value = mock_mime

        result = self.mixin._try_qimage_from_clipboard(
            mock_mime, mock_clipboard
        )
        self.assertIsNone(result)

    def test_try_qimage_from_clipboard_null_image(self):
        """Test _try_qimage_from_clipboard with null QImage."""
        mock_clipboard = MagicMock()
        mock_mime = MockMimeData()
        mock_mime._has_image = True

        # Create a null QImage
        qimg = QImage()
        mock_mime._image = qimg

        mock_clipboard.mimeData.return_value = mock_mime
        mock_clipboard.image.return_value = qimg

        result = self.mixin._try_qimage_from_clipboard(
            mock_mime, mock_clipboard
        )
        self.assertIsNone(result)

    def test_try_raw_image_from_clipboard_success(self):
        """Test _try_raw_image_from_clipboard with valid PNG data."""
        # Create a real PNG image in memory
        img = Image.new("RGBA", (50, 50), (255, 0, 0, 255))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        png_data = buffer.getvalue()

        mock_mime = MockMimeData()
        mock_mime._formats = ["image/png"]

        # Mock QByteArray with .data() method
        mock_byte_array = MagicMock()
        mock_byte_array.data.return_value = png_data
        mock_mime._data["image/png"] = mock_byte_array

        result = self.mixin._try_raw_image_from_clipboard(mock_mime)
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.size, (50, 50))

    def test_try_raw_image_from_clipboard_invalid_data(self):
        """Test _try_raw_image_from_clipboard with invalid data."""
        mock_mime = MockMimeData()
        mock_mime._formats = ["image/png"]

        # Mock QByteArray with invalid data
        mock_byte_array = MagicMock()
        mock_byte_array.data.return_value = b"not a valid image"
        mock_mime._data["image/png"] = mock_byte_array

        result = self.mixin._try_raw_image_from_clipboard(mock_mime)
        self.assertIsNone(result)

    def test_try_raw_image_from_clipboard_small_data(self):
        """Test _try_raw_image_from_clipboard with data too small."""
        mock_mime = MockMimeData()
        mock_mime._formats = ["image/png"]

        # Mock QByteArray with small data
        mock_byte_array = MagicMock()
        mock_byte_array.data.return_value = b"tiny"
        mock_mime._data["image/png"] = mock_byte_array

        result = self.mixin._try_raw_image_from_clipboard(mock_mime)
        self.assertIsNone(result)

    def test_try_url_from_clipboard_success(self):
        """Test _try_url_from_clipboard with valid image URL."""
        mock_mime = MockMimeData()
        mock_mime._has_urls = True

        mock_url = MagicMock()
        mock_url.toString.return_value = "https://example.com/image.png"
        mock_mime._urls = [mock_url]

        mock_img = Image.new("RGBA", (100, 100))
        self.mixin._load_image_from_url_or_file.return_value = mock_img

        result = self.mixin._try_url_from_clipboard(mock_mime)
        self.assertEqual(result, mock_img)
        self.mixin._load_image_from_url_or_file.assert_called_once_with(
            "https://example.com/image.png"
        )

    def test_try_url_from_clipboard_no_urls(self):
        """Test _try_url_from_clipboard when no URLs in clipboard."""
        mock_mime = MockMimeData()
        mock_mime._has_urls = False

        result = self.mixin._try_url_from_clipboard(mock_mime)
        self.assertIsNone(result)
        self.mixin._load_image_from_url_or_file.assert_not_called()

    def test_try_url_from_clipboard_load_failure(self):
        """Test _try_url_from_clipboard when image loading fails."""
        mock_mime = MockMimeData()
        mock_mime._has_urls = True

        mock_url = MagicMock()
        mock_url.toString.return_value = "https://example.com/image.png"
        mock_mime._urls = [mock_url]

        self.mixin._load_image_from_url_or_file.return_value = None

        result = self.mixin._try_url_from_clipboard(mock_mime)
        self.assertIsNone(result)

    def test_try_text_url_from_clipboard_http(self):
        """Test _try_text_url_from_clipboard with http URL."""
        mock_mime = MockMimeData()
        mock_mime._has_text = True
        mock_mime._text = "http://example.com/image.jpg"

        mock_img = Image.new("RGBA", (100, 100))
        self.mixin._load_image_from_url_or_file.return_value = mock_img

        result = self.mixin._try_text_url_from_clipboard(mock_mime)
        self.assertEqual(result, mock_img)
        self.mixin._load_image_from_url_or_file.assert_called_once_with(
            "http://example.com/image.jpg"
        )

    def test_try_text_url_from_clipboard_https(self):
        """Test _try_text_url_from_clipboard with https URL."""
        mock_mime = MockMimeData()
        mock_mime._has_text = True
        mock_mime._text = "https://example.com/image.png"

        mock_img = Image.new("RGBA", (100, 100))
        self.mixin._load_image_from_url_or_file.return_value = mock_img

        result = self.mixin._try_text_url_from_clipboard(mock_mime)
        self.assertEqual(result, mock_img)

    def test_try_text_url_from_clipboard_file(self):
        """Test _try_text_url_from_clipboard with file:// URL."""
        mock_mime = MockMimeData()
        mock_mime._has_text = True
        mock_mime._text = "file:///path/to/image.png"

        mock_img = Image.new("RGBA", (100, 100))
        self.mixin._load_image_from_url_or_file.return_value = mock_img

        result = self.mixin._try_text_url_from_clipboard(mock_mime)
        self.assertEqual(result, mock_img)

    def test_try_text_url_from_clipboard_no_text(self):
        """Test _try_text_url_from_clipboard with no text."""
        mock_mime = MockMimeData()
        mock_mime._has_text = False

        result = self.mixin._try_text_url_from_clipboard(mock_mime)
        self.assertIsNone(result)
        self.mixin._load_image_from_url_or_file.assert_not_called()

    def test_try_text_url_from_clipboard_non_url_text(self):
        """Test _try_text_url_from_clipboard with non-URL text."""
        mock_mime = MockMimeData()
        mock_mime._has_text = True
        mock_mime._text = "just some random text"

        result = self.mixin._try_text_url_from_clipboard(mock_mime)
        self.assertIsNone(result)
        self.mixin._load_image_from_url_or_file.assert_not_called()

    def test_paste_image_fallback_order(self):
        """Test that _paste_image_from_clipboard tries strategies in order."""
        mock_clipboard = MagicMock()
        mock_mime = MockMimeData()
        mock_clipboard.mimeData.return_value = mock_mime

        with patch(
            "airunner.components.art.gui.widgets.canvas.mixins.canvas_clipboard_mixin.QApplication.clipboard",
            return_value=mock_clipboard,
        ):
            with patch.object(
                self.mixin, "_try_qimage_from_clipboard"
            ) as mock_qimage:
                with patch.object(
                    self.mixin, "_try_raw_image_from_clipboard"
                ) as mock_raw:
                    with patch.object(
                        self.mixin, "_try_url_from_clipboard"
                    ) as mock_url:
                        with patch.object(
                            self.mixin, "_try_text_url_from_clipboard"
                        ) as mock_text:
                            # All strategies fail
                            mock_qimage.return_value = None
                            mock_raw.return_value = None
                            mock_url.return_value = None
                            mock_text.return_value = None

                            result = self.mixin._paste_image_from_clipboard()
                            self.assertIsNone(result)

                            # Verify all strategies were tried in order
                            mock_qimage.assert_called_once()
                            mock_raw.assert_called_once()
                            mock_url.assert_called_once()
                            mock_text.assert_called_once()

    def test_paste_image_first_strategy_success(self):
        """Test that _paste_image_from_clipboard stops after first success."""
        mock_clipboard = MagicMock()
        mock_mime = MockMimeData()
        mock_clipboard.mimeData.return_value = mock_mime

        mock_img = Image.new("RGBA", (100, 100))

        with patch(
            "airunner.components.art.gui.widgets.canvas.mixins.canvas_clipboard_mixin.QApplication.clipboard",
            return_value=mock_clipboard,
        ):
            with patch.object(
                self.mixin, "_try_qimage_from_clipboard"
            ) as mock_qimage:
                with patch.object(
                    self.mixin, "_try_raw_image_from_clipboard"
                ) as mock_raw:
                    with patch.object(
                        self.mixin, "_try_url_from_clipboard"
                    ) as mock_url:
                        with patch.object(
                            self.mixin, "_try_text_url_from_clipboard"
                        ) as mock_text:
                            # First strategy succeeds
                            mock_qimage.return_value = mock_img

                            result = self.mixin._paste_image_from_clipboard()
                            self.assertEqual(result, mock_img)

                            # Only first strategy should be called
                            mock_qimage.assert_called_once()
                            mock_raw.assert_not_called()
                            mock_url.assert_not_called()
                            mock_text.assert_not_called()


if __name__ == "__main__":
    unittest.main()
