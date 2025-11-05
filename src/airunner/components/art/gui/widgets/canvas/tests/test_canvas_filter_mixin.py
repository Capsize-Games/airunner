"""Unit tests for CanvasFilterMixin."""

import unittest
from unittest.mock import Mock
from PIL import Image

from airunner.components.art.gui.widgets.canvas.mixins.canvas_filter_mixin import (
    CanvasFilterMixin,
)


class TestCanvasFilterMixin(unittest.TestCase):
    """Test cases for CanvasFilterMixin functionality."""

    def setUp(self):
        """Set up test fixtures."""

        # Create a test class that includes the mixin
        class TestCanvas(CanvasFilterMixin):
            def __init__(self):
                self.settings_key = "drawing_pad_settings"
                self.current_active_image = None
                self.previewing_filter = False
                self.image_backup = None
                self.logger = Mock()
                self._load_image_from_object = Mock()
                self._add_image_to_undo = Mock(return_value=1)
                self._flush_pending_image = Mock()
                self._commit_layer_history_transaction = Mock()

        self.canvas = TestCanvas()

        # Create test images
        self.test_image = Image.new("RGB", (100, 100), color="red")
        self.filtered_image = Image.new("RGB", (100, 100), color="blue")

        # Create mock filter object
        self.mock_filter = Mock()
        self.mock_filter.filter = Mock(return_value=self.filtered_image)

    def test_on_apply_filter_signal_with_dict(self):
        """Test applying filter from dict message."""
        message = {"filter_object": self.mock_filter}
        self.canvas.current_active_image = self.test_image

        self.canvas.on_apply_filter_signal(message)

        self.mock_filter.filter.assert_called_once_with(self.test_image)
        self.canvas._load_image_from_object.assert_called_once()
        self.canvas._flush_pending_image.assert_called_once()

    def test_on_apply_filter_signal_with_object(self):
        """Test applying filter from direct filter object."""
        self.canvas.current_active_image = self.test_image

        self.canvas.on_apply_filter_signal(self.mock_filter)

        self.mock_filter.filter.assert_called_once_with(self.test_image)

    def test_on_cancel_filter_signal_with_backup(self):
        """Test cancelling filter when backup exists."""
        backup_image = Image.new("RGB", (100, 100), color="green")
        self.canvas.image_backup = backup_image
        self.canvas.previewing_filter = True

        self.canvas.on_cancel_filter_signal()

        self.canvas._load_image_from_object.assert_called_once()
        # Verify backup is cleared
        self.assertIsNone(self.canvas.image_backup)
        self.assertFalse(self.canvas.previewing_filter)

    def test_on_cancel_filter_signal_without_backup(self):
        """Test cancelling filter when no backup exists."""
        self.canvas.on_cancel_filter_signal()

        # Should not attempt to load image
        self.canvas._load_image_from_object.assert_not_called()

    def test_on_preview_filter_signal(self):
        """Test previewing a filter."""
        self.canvas.current_active_image = self.test_image
        message = {"filter_object": self.mock_filter}

        self.canvas.on_preview_filter_signal(message)

        self.mock_filter.filter.assert_called_once()
        self.canvas._load_image_from_object.assert_called_once()

    def test_apply_filter_success(self):
        """Test successful filter application."""
        self.canvas.current_active_image = self.test_image

        self.canvas._apply_filter(self.mock_filter)

        self.canvas._add_image_to_undo.assert_called_once()
        self.mock_filter.filter.assert_called_once_with(self.test_image)
        self.canvas._commit_layer_history_transaction.assert_called_once()
        self.assertFalse(self.canvas.previewing_filter)
        self.assertIsNone(self.canvas.image_backup)

    def test_apply_filter_wrong_settings_key(self):
        """Test filter application skipped for non-drawing-pad settings."""
        self.canvas.settings_key = "other_settings"
        self.canvas.current_active_image = self.test_image

        self.canvas._apply_filter(self.mock_filter)

        # Should not apply filter
        self.mock_filter.filter.assert_not_called()

    def test_apply_filter_no_image(self):
        """Test filter application when no image is active."""
        self.canvas.current_active_image = None

        self.canvas._apply_filter(self.mock_filter)

        # Should not apply filter
        self.mock_filter.filter.assert_not_called()

    def test_apply_filter_exception_handling(self):
        """Test filter application handles exceptions gracefully."""
        self.canvas.current_active_image = self.test_image
        self.mock_filter.filter.side_effect = Exception("Filter error")

        # Should not raise exception
        self.canvas._apply_filter(self.mock_filter)

        # Logger should be called
        self.canvas.logger.exception.assert_called()

    def test_cancel_filter_with_backup(self):
        """Test _cancel_filter returns backup image."""
        backup_image = Image.new("RGB", (100, 100), color="green")
        self.canvas.image_backup = backup_image
        self.canvas.previewing_filter = True

        result = self.canvas._cancel_filter()

        self.assertIsNotNone(result)
        self.assertIsNone(self.canvas.image_backup)
        self.assertFalse(self.canvas.previewing_filter)

    def test_cancel_filter_without_backup(self):
        """Test _cancel_filter returns None when no backup."""
        result = self.canvas._cancel_filter()

        self.assertIsNone(result)
        self.assertFalse(self.canvas.previewing_filter)

    def test_preview_filter_first_time(self):
        """Test previewing filter creates backup."""
        result = self.canvas._preview_filter(self.test_image, self.mock_filter)

        self.assertIsNotNone(result)
        self.assertIsNotNone(self.canvas.image_backup)
        self.assertTrue(self.canvas.previewing_filter)
        self.mock_filter.filter.assert_called_once()

    def test_preview_filter_subsequent_time(self):
        """Test previewing filter reuses backup."""
        # First preview
        self.canvas._preview_filter(self.test_image, self.mock_filter)
        first_backup = self.canvas.image_backup

        # Second preview
        self.canvas._preview_filter(self.test_image, self.mock_filter)

        # Backup should remain the same
        self.assertEqual(first_backup, self.canvas.image_backup)
        self.assertTrue(self.canvas.previewing_filter)

    def test_preview_filter_wrong_settings_key(self):
        """Test preview returns None for wrong settings key."""
        self.canvas.settings_key = "other_settings"

        result = self.canvas._preview_filter(self.test_image, self.mock_filter)

        self.assertIsNone(result)
        self.mock_filter.filter.assert_not_called()

    def test_preview_filter_no_image(self):
        """Test preview returns None when no image provided."""
        result = self.canvas._preview_filter(None, self.mock_filter)

        self.assertIsNone(result)
        self.mock_filter.filter.assert_not_called()


if __name__ == "__main__":
    unittest.main()
