"""Unit tests for CanvasDragDropMixin."""

import unittest
from unittest.mock import Mock, patch
from PIL import Image
import io

from airunner.components.art.gui.widgets.canvas.mixins.canvas_dragdrop_mixin import (
    CanvasDragDropMixin,
)


class TestCanvasDragDropMixin(unittest.TestCase):
    """Test cases for CanvasDragDropMixin functionality."""

    def setUp(self):
        """Set up test fixtures."""

        # Create a test class that includes the mixin
        class TestCanvas(CanvasDragDropMixin):
            def __init__(self):
                self.logger = Mock()
                self._add_image_to_undo = Mock(return_value=1)
                self._commit_layer_history_transaction = Mock()
                self.initialize_image = Mock()
                self._resize_image = Mock(side_effect=lambda img: img)
                self.update_drawing_pad_settings = Mock()
                self._add_image_to_scene = Mock()
                self.application_settings = Mock()
                self.application_settings.resize_on_paste = False
                self.current_active_image = None
                self._pending_image_binary = None
                self._current_active_image_binary = None
                self.api = Mock()

        self.canvas = TestCanvas()
        self.test_image = Image.new("RGB", (100, 100), color="red")

    def test_dragEnterEvent_valid_image_url(self):
        """Test drag enter with valid image URL."""
        mock_event = Mock()
        mock_url = Mock()
        mock_url.toString = Mock(return_value="file:///test.png")
        mock_event.mimeData().hasUrls = Mock(return_value=True)
        mock_event.mimeData().urls = Mock(return_value=[mock_url])

        self.canvas.dragEnterEvent(mock_event)

        mock_event.acceptProposedAction.assert_called_once()

    def test_dragEnterEvent_http_url(self):
        """Test drag enter with HTTP URL."""
        mock_event = Mock()
        mock_url = Mock()
        mock_url.toString = Mock(return_value="http://example.com/image.jpg")
        mock_event.mimeData().hasUrls = Mock(return_value=True)
        mock_event.mimeData().urls = Mock(return_value=[mock_url])

        self.canvas.dragEnterEvent(mock_event)

        mock_event.acceptProposedAction.assert_called_once()

    def test_dragEnterEvent_invalid_url(self):
        """Test drag enter with invalid URL."""
        mock_event = Mock()
        mock_url = Mock()
        mock_url.toString = Mock(return_value="file:///test.txt")
        mock_event.mimeData().hasFormat = Mock(return_value=False)
        mock_event.mimeData().hasUrls = Mock(return_value=True)
        mock_event.mimeData().urls = Mock(return_value=[mock_url])

        self.canvas.dragEnterEvent(mock_event)

        mock_event.ignore.assert_called_once()

    def test_dragMoveEvent_with_urls(self):
        """Test drag move event with URLs."""
        mock_event = Mock()
        mock_event.mimeData().hasUrls = Mock(return_value=True)

        self.canvas.dragMoveEvent(mock_event)

        mock_event.acceptProposedAction.assert_called_once()

    def test_handle_raw_image_drop_success(self):
        """Test successful raw image drop."""
        mock_mime = Mock()
        mock_mime.formats = Mock(return_value=["image/png"])

        # Create mock QByteArray-like object
        mock_data = Mock()
        mock_data.size = Mock(return_value=100)
        img_bytes = io.BytesIO()
        self.test_image.save(img_bytes, format="PNG")
        mock_data.data = Mock(return_value=img_bytes.getvalue())
        mock_mime.data = Mock(return_value=mock_data)

        with patch.object(
            self.canvas, "_process_dropped_image"
        ) as mock_process:
            result = self.canvas._handle_raw_image_drop(mock_mime)

            self.assertTrue(result)
            mock_process.assert_called_once()

    def test_handle_raw_image_drop_small_data(self):
        """Test raw image drop with data too small."""
        mock_mime = Mock()
        mock_mime.formats = Mock(return_value=["image/png"])

        mock_data = Mock()
        mock_data.size = Mock(return_value=5)  # Too small
        mock_mime.data = Mock(return_value=mock_data)

        result = self.canvas._handle_raw_image_drop(mock_mime)

        self.assertFalse(result)

    def test_handle_url_drop_success(self):
        """Test successful URL drop."""
        mock_mime = Mock()
        mock_url = Mock()
        mock_url.toString = Mock(return_value="/tmp/test.png")
        mock_url.toLocalFile = Mock(return_value="")
        mock_mime.urls = Mock(return_value=[mock_url])

        with patch.object(
            self.canvas,
            "_load_image_from_url_or_file",
            return_value=self.test_image,
        ):
            with patch.object(self.canvas, "_process_dropped_image"):
                result = self.canvas._handle_url_drop(mock_mime)

                self.assertTrue(result)

    def test_handle_url_drop_failure(self):
        """Test URL drop when image loading fails."""
        mock_mime = Mock()
        mock_url = Mock()
        mock_url.toString = Mock(return_value="/nonexistent/test.png")
        mock_url.toLocalFile = Mock(return_value="")
        mock_mime.urls = Mock(return_value=[mock_url])

        with patch.object(
            self.canvas, "_load_image_from_url_or_file", return_value=None
        ):
            result = self.canvas._handle_url_drop(mock_mime)

            self.assertFalse(result)

    def test_process_dropped_image(self):
        """Test processing a dropped image."""
        self.canvas._process_dropped_image(self.test_image)

        self.canvas._add_image_to_undo.assert_called_once()
        self.canvas.initialize_image.assert_called_once()
        self.canvas._commit_layer_history_transaction.assert_called_once_with(
            1, "image"
        )

    def test_process_dropped_image_with_resize(self):
        """Test processing dropped image with resize enabled."""
        self.canvas.application_settings.resize_on_paste = True

        self.canvas._process_dropped_image(self.test_image)

        self.canvas._resize_image.assert_called_once()

    @patch("requests.get")
    def test_load_image_from_url_http(self, mock_get):
        """Test loading image from HTTP URL."""
        img_bytes = io.BytesIO()
        self.test_image.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        mock_response = Mock()
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.canvas._load_image_from_url_or_file(
            "http://example.com/test.png"
        )

        self.assertIsNotNone(result)
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_load_image_from_url_http_failure(self, mock_get):
        """Test loading image from HTTP URL with failure."""
        mock_get.side_effect = Exception("Connection error")

        result = self.canvas._load_image_from_url_or_file(
            "http://example.com/test.png"
        )

        self.assertIsNone(result)
        self.canvas.logger.error.assert_called_once()

    @patch("os.path.exists")
    @patch("PIL.Image.open")
    def test_load_image_from_file_path(self, mock_open, mock_exists):
        """Test loading image from file path."""
        mock_exists.return_value = True
        mock_img = Mock()
        mock_img.convert = Mock(return_value=self.test_image)
        mock_open.return_value = mock_img

        result = self.canvas._load_image_from_url_or_file("/tmp/test.png")

        self.assertIsNotNone(result)
        mock_exists.assert_called_once()

    @patch("os.path.exists")
    def test_load_image_from_nonexistent_file(self, mock_exists):
        """Test loading image from nonexistent file."""
        mock_exists.return_value = False

        result = self.canvas._load_image_from_url_or_file(
            "/nonexistent/test.png"
        )

        self.assertIsNone(result)

    def test_load_image_from_object(self):
        """Test loading image from PIL Image object."""
        self.canvas._load_image_from_object(self.test_image, is_outpaint=True)

        self.canvas._add_image_to_scene.assert_called_once_with(
            is_outpaint=True, image=self.test_image, generated=False
        )

    def test_persist_dropped_image(self):
        """Test persisting dropped image."""
        rgba_image = self.test_image.convert("RGBA")

        self.canvas._persist_dropped_image(rgba_image, layer_id=1)

        self.canvas.update_drawing_pad_settings.assert_called_once()
        self.assertIsNotNone(self.canvas._pending_image_binary)
        self.assertIsNotNone(self.canvas._current_active_image_binary)

    def test_persist_dropped_image_converts_to_rgba(self):
        """Test persist dropped image converts to RGBA."""
        rgb_image = Image.new("RGB", (100, 100), color="blue")

        self.canvas._persist_dropped_image(rgb_image, layer_id=1)

        # Should convert to RGBA and persist
        self.canvas.update_drawing_pad_settings.assert_called_once()


if __name__ == "__main__":
    unittest.main()
