"""Tests for CanvasSceneManagementMixin layer item updates."""

import types
from types import SimpleNamespace

import pytest
from unittest.mock import Mock
from PIL import Image
from PySide6.QtCore import QPoint, QPointF
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
        scene.original_item_positions = {}
        scene.update_image_position = Mock()
        scene.update_drawing_pad_settings = Mock()
        scene._get_current_selected_layer_id = Mock(return_value=3)
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

    def test_layer_canvas_does_not_fall_back_to_legacy_item(
        self,
        mock_scene,
        sample_image,
        sample_qimage,
    ):
        """Layer canvases should not update a stale legacy self.item."""
        mock_layer_item = Mock()
        mock_scene.item = Mock()
        mock_scene.canvas_type = "brush"
        mock_scene._layer_items = {7: mock_layer_item}
        mock_scene._get_active_layer_item.return_value = None
        mock_scene._get_layer_canvas_item = Mock(return_value=mock_layer_item)
        mock_scene._uses_layer_canvas = Mock(return_value=True)
        mock_scene._remove_legacy_item_if_present = Mock()
        mock_scene._convert_and_cache_qimage.return_value = sample_qimage

        from airunner.components.art.gui.widgets.canvas.mixins.canvas_scene_management_mixin import (
            CanvasSceneManagementMixin,
        )

        CanvasSceneManagementMixin._update_or_create_item(
            mock_scene,
            sample_image,
            QPoint(0, 0),
            QPoint(0, 0),
        )

        mock_layer_item.updateImage.assert_called_once_with(sample_qimage)
        mock_scene._remove_legacy_item_if_present.assert_called_once_with()
        mock_scene._update_existing_item_image.assert_not_called()
        mock_scene._update_item_position.assert_not_called()

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

    def test_generated_layer_item_moves_to_active_grid_position(
        self,
        mock_scene,
        sample_image,
        sample_qimage,
    ):
        """Generated images should move the active layer to the grid."""
        mock_layer_item = Mock()
        mock_scene._get_active_layer_item.return_value = mock_layer_item
        mock_scene._convert_and_cache_qimage.return_value = sample_qimage

        from airunner.components.art.gui.widgets.canvas.mixins.canvas_scene_management_mixin import (
            CanvasSceneManagementMixin,
        )

        mock_scene._update_active_layer_item_position = types.MethodType(
            CanvasSceneManagementMixin._update_active_layer_item_position,
            mock_scene,
        )

        CanvasSceneManagementMixin._update_or_create_item(
            mock_scene,
            sample_image,
            QPoint(128, 256),
            QPointF(0, 0),
            generated=True,
        )

        assert mock_scene.original_item_positions[mock_layer_item] == QPointF(
            128,
            256,
        )
        mock_scene.update_drawing_pad_settings.assert_called_once_with(
            layer_id=3,
            x_pos=128,
            y_pos=256,
        )
        mock_scene.update_image_position.assert_called_once_with(
            QPointF(0, 0),
            {mock_layer_item: QPointF(128, 256)},
        )

    def test_update_item_position_uses_grid_compensation(self, mock_scene):
        """Legacy item positioning should honor view grid compensation."""
        mock_item = Mock()
        mock_item.pos.return_value = QPointF(0, 0)
        mock_item.setPos = Mock()
        mock_scene.item = mock_item
        mock_scene.views = Mock(
            return_value=[
                SimpleNamespace(
                    grid_compensation_offset=QPointF(25, 5)
                )
            ]
        )

        from airunner.components.art.gui.widgets.canvas.mixins.canvas_scene_management_mixin import (
            CanvasSceneManagementMixin,
        )

        CanvasSceneManagementMixin._update_item_position(
            mock_scene,
            QPoint(100, 50),
            QPointF(10, 20),
        )

        assert mock_scene.original_item_positions[mock_item] == QPointF(
            100,
            50,
        )
        mock_item.setPos.assert_called_once_with(QPointF(115, 35))
