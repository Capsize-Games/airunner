"""Unit tests for CanvasTransformMixin."""

import unittest
from unittest.mock import Mock, patch
from PIL import Image

from airunner.components.art.gui.widgets.canvas.mixins.canvas_transform_mixin import (
    CanvasTransformMixin,
)


class TestCanvasTransformMixin(unittest.TestCase):
    """Test cases for CanvasTransformMixin functionality."""

    def setUp(self):
        """Set up test fixtures."""

        # Create a test class that includes the mixin
        class TestCanvas(CanvasTransformMixin):
            def __init__(self):
                self.current_active_image = None
                self.logger = Mock()
                self._add_image_to_undo = Mock(return_value=1)
                self._commit_layer_history_transaction = Mock()
                self.initialize_image = Mock()
                self.delete_image = Mock()
                self.application_settings = Mock()
                self.application_settings.working_width = 512
                self.application_settings.working_height = 512

        self.canvas = TestCanvas()
        self.test_image = Image.new("RGB", (200, 200), color="red")

    def test_on_canvas_copy_image_signal(self):
        """Test copy image signal handler."""
        self.canvas.current_active_image = self.test_image

        with patch.object(
            self.canvas, "_copy_image", return_value=self.test_image
        ) as mock_copy:
            self.canvas.on_canvas_copy_image_signal()
            mock_copy.assert_called_once_with(self.test_image)

    def test_on_canvas_cut_image_signal(self):
        """Test cut image signal handler."""
        self.canvas.current_active_image = self.test_image

        with patch.object(
            self.canvas, "_cut_image", return_value=self.test_image
        ) as mock_cut:
            self.canvas.on_canvas_cut_image_signal()
            mock_cut.assert_called_once_with(self.test_image)

    def test_on_canvas_rotate_90_clockwise_signal(self):
        """Test rotate clockwise signal handler."""
        with patch.object(self.canvas, "_rotate_90_clockwise") as mock_rotate:
            self.canvas.on_canvas_rotate_90_clockwise_signal()
            mock_rotate.assert_called_once()

    def test_on_canvas_rotate_90_counterclockwise_signal(self):
        """Test rotate counterclockwise signal handler."""
        with patch.object(
            self.canvas, "_rotate_90_counterclockwise"
        ) as mock_rotate:
            self.canvas.on_canvas_rotate_90_counterclockwise_signal()
            mock_rotate.assert_called_once()

    def test_rotate_image_success(self):
        """Test successful image rotation."""
        self.canvas.current_active_image = self.test_image

        self.canvas.rotate_image(45)

        self.canvas._add_image_to_undo.assert_called_once()
        self.canvas.initialize_image.assert_called_once()
        self.canvas._commit_layer_history_transaction.assert_called_once_with(
            1, "image"
        )

    def test_rotate_image_no_image(self):
        """Test rotation when no image is active."""
        self.canvas.current_active_image = None

        self.canvas.rotate_image(45)

        # Should not attempt undo or commit
        self.canvas._add_image_to_undo.assert_not_called()
        self.canvas._commit_layer_history_transaction.assert_not_called()

    def test_rotate_90_clockwise(self):
        """Test 90 degree clockwise rotation."""
        self.canvas.current_active_image = self.test_image

        with patch.object(self.canvas, "rotate_image") as mock_rotate:
            self.canvas._rotate_90_clockwise()
            mock_rotate.assert_called_once_with(-90)

    def test_rotate_90_counterclockwise(self):
        """Test 90 degree counterclockwise rotation."""
        self.canvas.current_active_image = self.test_image

        with patch.object(self.canvas, "rotate_image") as mock_rotate:
            self.canvas._rotate_90_counterclockwise()
            mock_rotate.assert_called_once_with(90)

    def test_copy_image(self):
        """Test copy image delegates to clipboard move."""
        with patch.object(
            self.canvas,
            "_move_pixmap_to_clipboard",
            return_value=self.test_image,
        ) as mock_clipboard:
            result = self.canvas._copy_image(self.test_image)

            mock_clipboard.assert_called_once_with(self.test_image)
            self.assertEqual(result, self.test_image)

    @patch("subprocess.Popen")
    def test_move_pixmap_to_clipboard_success(self, mock_popen):
        """Test moving image to clipboard successfully."""
        mock_process = Mock()
        mock_process.communicate = Mock(return_value=(b"", b""))
        mock_popen.return_value = mock_process

        result = self.canvas._move_pixmap_to_clipboard(self.test_image)

        self.assertEqual(result, self.test_image)
        mock_popen.assert_called_once()
        # Verify xclip command structure
        args = mock_popen.call_args[0][0]
        self.assertEqual(args[0], "xclip")
        self.assertIn("clipboard", args)

    def test_move_pixmap_to_clipboard_none_image(self):
        """Test clipboard move with None image."""
        result = self.canvas._move_pixmap_to_clipboard(None)

        self.assertIsNone(result)
        self.canvas.logger.warning.assert_called_once()

    def test_move_pixmap_to_clipboard_invalid_type(self):
        """Test clipboard move with invalid image type."""
        result = self.canvas._move_pixmap_to_clipboard("not_an_image")

        self.assertIsNone(result)
        self.canvas.logger.warning.assert_called_once()

    @patch("subprocess.Popen")
    def test_move_pixmap_to_clipboard_xclip_missing(self, mock_popen):
        """Test clipboard move when xclip is not installed."""
        mock_popen.side_effect = FileNotFoundError()

        result = self.canvas._move_pixmap_to_clipboard(self.test_image)

        self.assertEqual(result, self.test_image)
        self.canvas.logger.error.assert_called_once()

    def test_cut_image_success(self):
        """Test successful image cut operation."""
        self.canvas.current_active_image = self.test_image

        with patch.object(
            self.canvas, "_copy_image", return_value=self.test_image
        ):
            result = self.canvas._cut_image(self.test_image)

            self.assertEqual(result, self.test_image)
            self.canvas.delete_image.assert_called_once()
            self.canvas._add_image_to_undo.assert_called_once()
            self.canvas._commit_layer_history_transaction.assert_called_once()

    def test_cut_image_copy_failed(self):
        """Test cut operation when copy fails."""
        with patch.object(self.canvas, "_copy_image", return_value=None):
            self.canvas._cut_image(self.test_image)

            # Should not delete or modify history
            self.canvas.delete_image.assert_not_called()
            self.canvas._add_image_to_undo.assert_not_called()

    def test_resize_image_success(self):
        """Test successful image resize."""
        large_image = Image.new("RGB", (1024, 1024), color="blue")

        result = self.canvas._resize_image(large_image)

        self.assertIsNotNone(result)
        # Image should be thumbnailed to working dimensions
        self.assertLessEqual(result.width, 512)
        self.assertLessEqual(result.height, 512)

    def test_resize_image_none(self):
        """Test resize with None image."""
        result = self.canvas._resize_image(None)

        self.assertIsNone(result)

    def test_resize_image_preserves_aspect_ratio(self):
        """Test resize preserves aspect ratio."""
        # Create a wide image
        wide_image = Image.new("RGB", (1000, 500), color="green")

        result = self.canvas._resize_image(wide_image)

        # Aspect ratio should be preserved (2:1)
        original_ratio = 1000 / 500
        result_ratio = result.width / result.height
        self.assertAlmostEqual(original_ratio, result_ratio, places=1)


if __name__ == "__main__":
    unittest.main()
