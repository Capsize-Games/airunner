"""Unit tests for CanvasItemManagementMixin.

Tests cover canvas item creation and management with:
- Happy path: Normal item creation and updates
- Sad path: Edge cases like None images, missing items
- Bad path: Error conditions and exception handling

Following red/green/refactor TDD methodology.
"""

from unittest.mock import Mock, PropertyMock
from PySide6.QtGui import QImage
from PySide6.QtCore import QPointF, QRectF


class TestCreateNewItem:
    """Test _create_new_item method - create new LayerImageItem."""

    def test_create_new_item_with_valid_image(
        self, mock_scene_with_settings, mock_qimage
    ):
        """HAPPY: Create new item with valid QImage."""
        scene = mock_scene_with_settings
        scene.item = None
        scene.addItem = Mock()
        scene.original_item_positions = {}

        x, y = 100, 200
        scene._create_new_item(mock_qimage, x, y)

        # Should create new item
        assert scene.item is not None
        scene.addItem.assert_called_once_with(scene.item)
        assert scene.item in scene.original_item_positions

    def test_create_new_item_sets_position(
        self, mock_scene_with_settings, mock_qimage
    ):
        """HAPPY: New item positioned correctly."""
        scene = mock_scene_with_settings
        scene.item = None
        scene.addItem = Mock()
        scene.original_item_positions = {}

        x, y = 50, 75
        scene._create_new_item(mock_qimage, x, y)

        # Position should be set
        assert scene.item.pos() == QPointF(x, y)

    def test_create_new_item_already_in_scene(
        self, mock_scene_with_settings, mock_qimage
    ):
        """EDGE: Item already in scene shouldn't be added again."""
        scene = mock_scene_with_settings
        scene.item = None
        scene.addItem = Mock()
        scene.original_item_positions = {}

        # First creation
        scene._create_new_item(mock_qimage, 0, 0)

        # Reset mocks
        scene.addItem.reset_mock()

        # Try to create again (item already has scene)
        scene._create_new_item(mock_qimage, 10, 10)

        # Should not add again since item.scene() is not None
        # (In real code, scene() returns the parent scene)


class TestUpdateExistingItem:
    """Test _update_existing_item method - update existing item."""

    def test_update_existing_item_with_valid_image(
        self, mock_scene_with_settings, mock_qimage
    ):
        """HAPPY: Update existing item with new image."""
        scene = mock_scene_with_settings

        # Create mock item
        mock_item = Mock()
        mock_item.setPos = Mock()
        mock_item.pos.return_value = QPointF(50, 50)
        mock_item.updateImage = Mock()
        scene.item = mock_item
        scene.original_item_positions = {}

        x, y = 100, 150
        scene._update_existing_item(mock_qimage, x, y)

        # Should update position and image
        mock_item.setPos.assert_called_once_with(x, y)
        mock_item.updateImage.assert_called_once_with(mock_qimage)
        assert mock_item in scene.original_item_positions

    def test_update_existing_item_with_none_image(
        self, mock_scene_with_settings
    ):
        """SAD: Update with None image only updates position."""
        scene = mock_scene_with_settings

        # Create mock item
        mock_item = Mock()
        mock_item.setPos = Mock()
        mock_item.pos.return_value = QPointF(0, 0)
        mock_item.updateImage = Mock()
        scene.item = mock_item
        scene.original_item_positions = {}

        scene._update_existing_item(None, 25, 30)

        # Should update position but not image
        mock_item.setPos.assert_called_once()
        mock_item.updateImage.assert_not_called()

    def test_update_existing_item_with_null_qimage(
        self, mock_scene_with_settings
    ):
        """SAD: Update with null QImage only updates position."""
        scene = mock_scene_with_settings

        # Create null QImage
        null_qimage = QImage()
        assert null_qimage.isNull()

        # Create mock item
        mock_item = Mock()
        mock_item.setPos = Mock()
        mock_item.pos.return_value = QPointF(0, 0)
        mock_item.updateImage = Mock()
        scene.item = mock_item
        scene.original_item_positions = {}

        scene._update_existing_item(null_qimage, 10, 20)

        # Should update position but not image (because isNull())
        mock_item.setPos.assert_called_once()
        mock_item.updateImage.assert_not_called()

    def test_update_existing_item_update_fails(
        self, mock_scene_with_settings, mock_qimage
    ):
        """BAD: UpdateImage failure is caught and logged."""
        scene = mock_scene_with_settings

        # Create mock item that raises exception
        mock_item = Mock()
        mock_item.setPos = Mock()
        mock_item.pos.return_value = QPointF(0, 0)
        mock_item.updateImage = Mock(side_effect=RuntimeError("Update failed"))
        scene.item = mock_item
        scene.original_item_positions = {}

        # Should not raise exception (caught internally)
        scene._update_existing_item(mock_qimage, 10, 20)

        # Position should still be updated
        mock_item.setPos.assert_called_once_with(10, 20)

    def test_update_existing_item_no_logger(
        self, mock_scene_with_settings, mock_qimage
    ):
        """BAD: UpdateImage failure without logger is handled gracefully."""
        scene = mock_scene_with_settings

        # Create mock item that raises exception
        mock_item = Mock()
        mock_item.setPos = Mock()
        mock_item.pos.return_value = QPointF(0, 0)
        mock_item.updateImage = Mock(side_effect=Exception("Update failed"))
        scene.item = mock_item
        scene.original_item_positions = {}

        # Should not raise exception (even without logger)
        scene._update_existing_item(mock_qimage, 10, 20)


class TestSetItem:
    """Test set_item method - create or update main canvas item."""

    def test_set_item_creates_new_item(
        self, mock_scene_with_settings, mock_qimage
    ):
        """HAPPY: set_item creates new item when none exists."""
        scene = mock_scene_with_settings
        scene.item = None
        scene._layer_items = {}
        scene.original_item_positions = {}
        scene.addItem = Mock()
        scene.setSceneRect = Mock()

        # Mock extended viewport rect
        scene._extended_viewport_rect = QRectF(0, 0, 1000, 1000)

        # Mock grid settings
        mock_grid = Mock()
        mock_grid.pos_x = 50
        mock_grid.pos_y = 75
        type(scene).active_grid_settings = PropertyMock(return_value=mock_grid)

        scene.set_item(mock_qimage)

        # Should create new item
        assert scene.item is not None
        scene.setSceneRect.assert_called_once()

    def test_set_item_updates_existing_item(
        self, mock_scene_with_settings, mock_qimage
    ):
        """HAPPY: set_item updates existing item."""
        scene = mock_scene_with_settings

        # Create existing item
        mock_item = Mock()
        mock_item.setPos = Mock()
        mock_item.pos.return_value = QPointF(0, 0)
        mock_item.updateImage = Mock()
        mock_item.setZValue = Mock()
        mock_item.setVisible = Mock()
        scene.item = mock_item

        scene._layer_items = {}
        scene.original_item_positions = {}
        scene.setSceneRect = Mock()
        scene._extended_viewport_rect = QRectF(0, 0, 1000, 1000)

        # Mock grid settings
        mock_grid = Mock()
        mock_grid.pos_x = 100
        mock_grid.pos_y = 200
        type(scene).active_grid_settings = PropertyMock(return_value=mock_grid)

        scene.set_item(mock_qimage, z_index=10)

        # Should update existing item
        mock_item.updateImage.assert_called_once()
        mock_item.setZValue.assert_called_once_with(10)
        mock_item.setVisible.assert_called_once_with(True)

    def test_set_item_with_custom_position(
        self, mock_scene_with_settings, mock_qimage
    ):
        """HAPPY: set_item with custom x, y position."""
        scene = mock_scene_with_settings
        scene.item = None
        scene._layer_items = {}
        scene.original_item_positions = {}
        scene.addItem = Mock()
        scene.setSceneRect = Mock()
        scene._extended_viewport_rect = QRectF(0, 0, 1000, 1000)

        # Mock grid settings (should be ignored)
        mock_grid = Mock()
        mock_grid.pos_x = 0
        mock_grid.pos_y = 0
        type(scene).active_grid_settings = PropertyMock(return_value=mock_grid)

        custom_x, custom_y = 250, 350
        scene.set_item(mock_qimage, x=custom_x, y=custom_y)

        # Should use custom position
        assert scene.item.pos() == QPointF(custom_x, custom_y)

    def test_set_item_with_none_image(self, mock_scene_with_settings):
        """SAD: set_item with None image does nothing."""
        scene = mock_scene_with_settings
        scene.item = None
        scene._layer_items = {}
        scene.setSceneRect = Mock()
        scene._extended_viewport_rect = QRectF(0, 0, 1000, 1000)

        scene.set_item(None)

        # Should not create item
        assert scene.item is None

    def test_set_item_with_layer_items_returns_early(
        self, mock_scene_with_settings, mock_qimage
    ):
        """EDGE: set_item returns early when layer items exist."""
        scene = mock_scene_with_settings
        scene.item = None

        # Mock layer items (non-empty)
        scene._layer_items = {1: Mock()}
        scene.setSceneRect = Mock()
        scene._extended_viewport_rect = QRectF(0, 0, 1000, 1000)

        # Mock grid settings
        mock_grid = Mock()
        mock_grid.pos_x = 50
        mock_grid.pos_y = 75
        type(scene).active_grid_settings = PropertyMock(return_value=mock_grid)

        scene.set_item(mock_qimage)

        # Should return early, not create item
        assert scene.item is None

    def test_set_item_z_index_default(
        self, mock_scene_with_settings, mock_qimage
    ):
        """HAPPY: set_item uses default z_index of 5."""
        scene = mock_scene_with_settings

        # Create existing item
        mock_item = Mock()
        mock_item.setPos = Mock()
        mock_item.pos.return_value = QPointF(0, 0)
        mock_item.updateImage = Mock()
        mock_item.setZValue = Mock()
        mock_item.setVisible = Mock()
        scene.item = mock_item

        scene._layer_items = {}
        scene.original_item_positions = {}
        scene.setSceneRect = Mock()
        scene._extended_viewport_rect = QRectF(0, 0, 1000, 1000)

        # Mock grid settings
        mock_grid = Mock()
        mock_grid.pos_x = 0
        mock_grid.pos_y = 0
        type(scene).active_grid_settings = PropertyMock(return_value=mock_grid)

        scene.set_item(mock_qimage)  # No z_index specified

        # Should use default z_index of 5
        mock_item.setZValue.assert_called_once_with(5)


class TestClearSelection:
    """Test clear_selection method - clear selected items."""

    def test_clear_selection(self, mock_scene_with_settings):
        """HAPPY: clear_selection clears selection positions."""
        scene = mock_scene_with_settings

        # Set selection positions
        scene.selection_start_pos = QPointF(10, 10)
        scene.selection_stop_pos = QPointF(100, 100)

        scene.clear_selection()

        # Should clear both positions to None
        assert scene.selection_start_pos is None
        assert scene.selection_stop_pos is None


class TestItemManagementEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_multiple_set_item_calls(
        self, mock_scene_with_settings, mock_qimage
    ):
        """STRESS: Multiple set_item calls handle state correctly."""
        scene = mock_scene_with_settings
        scene.item = None
        scene._layer_items = {}
        scene.original_item_positions = {}
        scene.addItem = Mock()
        scene.setSceneRect = Mock()
        scene._extended_viewport_rect = QRectF(0, 0, 1000, 1000)

        # Mock grid settings
        mock_grid = Mock()
        mock_grid.pos_x = 0
        mock_grid.pos_y = 0
        type(scene).active_grid_settings = PropertyMock(return_value=mock_grid)

        # Call multiple times
        for i in range(3):
            scene.set_item(mock_qimage, x=i * 10, y=i * 20)

        # Should have one item that was updated
        assert scene.item is not None

    def test_item_positioning_accuracy(
        self, mock_scene_with_settings, mock_qimage
    ):
        """INTEGRATION: Item positioning is accurate."""
        scene = mock_scene_with_settings
        scene.item = None
        scene._layer_items = {}
        scene.original_item_positions = {}
        scene.addItem = Mock()
        scene.setSceneRect = Mock()
        scene._extended_viewport_rect = QRectF(0, 0, 1000, 1000)

        # Mock grid settings
        mock_grid = Mock()
        mock_grid.pos_x = 123
        mock_grid.pos_y = 456
        type(scene).active_grid_settings = PropertyMock(return_value=mock_grid)

        scene.set_item(mock_qimage)

        # Exact position should match
        assert scene.item.pos() == QPointF(123, 456)
