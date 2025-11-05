"""Tests for CanvasSceneManagementMixin layer item updates."""

import pytest
from unittest.mock import Mock
from PIL import Image
from PySide6.QtCore import QPoint
from PySide6.QtGui import QImage


class TestCanvasSceneManagementMixin:
    """Test suite for CanvasSceneManagementMixin._update_or_create_item."""

    @pytest.fixture
    def mock_scene(self):
        """Create a mock scene with necessary attributes."""
        scene = Mock()
        scene.item = None
        scene._layer_items = {}
        scene.current_active_image = None
        scene.logger = Mock()
        scene._get_active_layer_item = Mock(return_value=None)
        scene._convert_and_cache_qimage = Mock()
        scene._update_existing_item_image = Mock()
        scene._update_item_position = Mock()
        return scene

    @pytest.fixture
    def sample_image(self):
        """Create a sample PIL Image."""
        return Image.new("RGB", (256, 256), color="red")

    @pytest.fixture
    def sample_qimage(self):
        """Create a sample QImage."""
        return QImage(256, 256, QImage.Format.Format_RGB888)

    def test_update_active_layer_item_success(
        self, mock_scene, sample_image, sample_qimage
    ):
        """Test that filter updates active layer item when it exists."""
        # Setup: Mock active layer item exists
        mock_layer_item = Mock()
        mock_scene._get_active_layer_item.return_value = mock_layer_item
        mock_scene._convert_and_cache_qimage.return_value = sample_qimage

        # Import the mixin class
        from airunner.components.art.gui.widgets.canvas.mixins.canvas_scene_management_mixin import (
            CanvasSceneManagementMixin,
        )

        # Call the method
        CanvasSceneManagementMixin._update_or_create_item(
            mock_scene, sample_image, QPoint(0, 0), QPoint(0, 0)
        )

        # Verify layer item was updated
        mock_layer_item.updateImage.assert_called_once_with(sample_qimage)
        # Verify current_active_image was also set
        assert mock_scene.current_active_image == sample_image
        # Verify old system was NOT used
        mock_scene._update_existing_item_image.assert_not_called()

    def test_fallback_to_self_item_when_no_layer(
        self, mock_scene, sample_image, sample_qimage
    ):
        """Test fallback to self.item when no active layer item exists."""
        # Setup: No active layer, but self.item exists
        mock_scene._get_active_layer_item.return_value = None
        mock_scene.item = Mock()
        mock_scene._convert_and_cache_qimage.return_value = sample_qimage

        from airunner.components.art.gui.widgets.canvas.mixins.canvas_scene_management_mixin import (
            CanvasSceneManagementMixin,
        )

        # Call the method
        CanvasSceneManagementMixin._update_or_create_item(
            mock_scene, sample_image, QPoint(0, 0), QPoint(0, 0)
        )

        # Verify old system was used
        mock_scene._update_existing_item_image.assert_called_once_with(
            sample_qimage
        )
        mock_scene._update_item_position.assert_called_once()

    def test_property_fallback_when_no_items(self, mock_scene, sample_image):
        """Test setting property when neither layer nor self.item exists."""
        # Setup: No active layer, no self.item
        mock_scene._get_active_layer_item.return_value = None
        mock_scene.item = None

        from airunner.components.art.gui.widgets.canvas.mixins.canvas_scene_management_mixin import (
            CanvasSceneManagementMixin,
        )

        # Call the method
        CanvasSceneManagementMixin._update_or_create_item(
            mock_scene, sample_image, QPoint(0, 0), QPoint(0, 0)
        )

        # Verify only property was set
        assert mock_scene.current_active_image == sample_image
        mock_scene._update_existing_item_image.assert_not_called()

    def test_null_qimage_handling_for_layer(self, mock_scene, sample_image):
        """Test that null QImage is handled gracefully for layer items."""
        # Setup: Active layer exists but conversion fails
        mock_layer_item = Mock()
        mock_scene._get_active_layer_item.return_value = mock_layer_item
        mock_scene._convert_and_cache_qimage.return_value = None

        from airunner.components.art.gui.widgets.canvas.mixins.canvas_scene_management_mixin import (
            CanvasSceneManagementMixin,
        )

        # Call the method
        CanvasSceneManagementMixin._update_or_create_item(
            mock_scene, sample_image, QPoint(0, 0), QPoint(0, 0)
        )

        # Verify layer item was NOT updated
        mock_layer_item.updateImage.assert_not_called()
        # Verify warning was logged
        mock_scene.logger.warning.assert_called_once()

    def test_layer_update_exception_handling(
        self, mock_scene, sample_image, sample_qimage
    ):
        """Test exception handling when updating layer item fails."""
        # Setup: Layer update throws exception
        mock_layer_item = Mock()
        mock_layer_item.updateImage.side_effect = RuntimeError("Item deleted")
        mock_scene._get_active_layer_item.return_value = mock_layer_item
        mock_scene._convert_and_cache_qimage.return_value = sample_qimage

        from airunner.components.art.gui.widgets.canvas.mixins.canvas_scene_management_mixin import (
            CanvasSceneManagementMixin,
        )

        # Call should not raise exception
        CanvasSceneManagementMixin._update_or_create_item(
            mock_scene, sample_image, QPoint(0, 0), QPoint(0, 0)
        )

        # Verify error was logged
        mock_scene.logger.error.assert_called_once()
