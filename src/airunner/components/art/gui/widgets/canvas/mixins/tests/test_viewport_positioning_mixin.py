"""Tests for ViewportPositioningMixin."""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QPointF, QSize

from airunner.components.art.gui.widgets.canvas.mixins.viewport_positioning_mixin import (
    ViewportPositioningMixin,
)


class TestableViewportPositioningMixin(ViewportPositioningMixin):
    """Testable version of ViewportPositioningMixin with required dependencies."""

    def __init__(self):
        self.center_pos = QPointF(0, 0)
        self._grid_compensation_offset = QPointF(0, 0)
        self.canvas_offset = QPointF(0, 0)
        self.canvas_offset_x = 0
        self.canvas_offset_y = 0
        self.logger = MagicMock()
        self.active_grid_area = None
        self.active_grid_settings = MagicMock()
        self.active_grid_settings.pos_x = 100
        self.active_grid_settings.pos_y = 100
        self.active_grid_settings.pos = (100, 100)
        self.application_settings = MagicMock()
        self.application_settings.working_width = 1024
        self.application_settings.working_height = 1024
        self._scene = None
        self._is_restoring_state = False
        self._initialized = True

    @property
    def scene(self):
        """Mock scene property."""
        return self._scene

    @scene.setter
    def scene(self, value):
        """Mock scene setter."""
        self._scene = value

    def viewport(self):
        """Mock viewport method."""
        mock_viewport = MagicMock()
        mock_viewport.size.return_value = QSize(800, 600)
        mock_viewport.update = MagicMock()
        return mock_viewport

    def update_active_grid_settings(self, **kwargs):
        """Mock update_active_grid_settings method."""


@pytest.fixture
def mixin(qapp):
    """Create a testable viewport positioning mixin instance."""
    return TestableViewportPositioningMixin()


@pytest.fixture
def mock_scene():
    """Create a mock scene."""
    scene = MagicMock()
    scene.is_dragging = False
    scene._layer_items = {}
    scene.update_image_position = MagicMock()
    return scene


class TestViewportCenterProperty:
    """Test viewport_center property."""

    def test_viewport_center_calculates_correctly(self, mixin):
        """Test that viewport_center returns center point of viewport."""
        center = mixin.viewport_center

        assert isinstance(center, QPointF)
        assert center.x() == 400  # 800 / 2
        assert center.y() == 300  # 600 / 2


class TestGetRecenteredPosition:
    """Test get_recentered_position method."""

    def test_get_recentered_position_centers_item(self, mixin):
        """Test that item is centered in viewport."""
        width, height = 100, 100

        x, y = mixin.get_recentered_position(width, height)

        # Should position item so its center aligns with viewport center
        assert x == 350  # 400 (center) - 50 (half width)
        assert y == 250  # 300 (center) - 50 (half height)

    def test_get_recentered_position_handles_large_items(self, mixin):
        """Test positioning of items larger than viewport."""
        width, height = 1000, 800

        x, y = mixin.get_recentered_position(width, height)

        # Calculation should still work even if resulting position is negative
        assert x == -100  # 400 - 500
        assert y == -100  # 300 - 400


class TestOriginalItemPositions:
    """Test original_item_positions method."""

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.viewport_positioning_mixin.CanvasLayer"
    )
    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.viewport_positioning_mixin.DrawingPadSettings"
    )
    def test_original_item_positions_returns_saved_positions(
        self, mock_settings_class, mock_layer_class, mixin, mock_scene
    ):
        """Test that saved positions are returned from database."""
        mixin._scene = mock_scene

        # Mock layer data
        mock_layer = MagicMock()
        mock_layer.id = 1
        mock_layer_class.objects.order_by.return_value.all.return_value = [
            mock_layer
        ]

        # Mock settings with saved position
        mock_settings = MagicMock()
        mock_settings.x_pos = 100
        mock_settings.y_pos = 200
        mock_settings_class.objects.filter_by.return_value = [mock_settings]

        # Mock scene item
        mock_item = MagicMock()
        mock_scene._layer_items[1] = mock_item

        positions = mixin.original_item_positions()

        assert mock_item in positions
        assert positions[mock_item] == QPointF(100, 200)

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.viewport_positioning_mixin.CanvasLayer"
    )
    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.viewport_positioning_mixin.DrawingPadSettings"
    )
    def test_original_item_positions_calculates_default_when_none(
        self, mock_settings_class, mock_layer_class, mixin, mock_scene
    ):
        """Test that default position is calculated when no saved position."""
        mixin._scene = mock_scene

        # Mock layer
        mock_layer = MagicMock()
        mock_layer.id = 1
        mock_layer_class.objects.order_by.return_value.all.return_value = [
            mock_layer
        ]

        # Mock settings with no saved position
        mock_settings = MagicMock()
        mock_settings.id = 1
        mock_settings.x_pos = None
        mock_settings.y_pos = None
        mock_settings_class.objects.filter_by.return_value = [mock_settings]
        mock_settings_class.objects.update = MagicMock()

        # Mock scene item with bounds
        mock_item = MagicMock()
        mock_rect = MagicMock()
        mock_rect.width.return_value = 100
        mock_rect.height.return_value = 100
        mock_item.boundingRect.return_value = mock_rect
        mock_scene._layer_items[1] = mock_item

        positions = mixin.original_item_positions()

        # Should have calculated and saved position
        assert mock_item in positions
        mock_settings_class.objects.update.assert_called_once()


class TestRecenterLayerPositions:
    """Test recenter_layer_positions method."""

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.viewport_positioning_mixin.CanvasLayer"
    )
    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.viewport_positioning_mixin.DrawingPadSettings"
    )
    def test_recenter_layer_positions_recalculates_and_saves(
        self, mock_settings_class, mock_layer_class, mixin, mock_scene
    ):
        """Test that layer positions are recalculated and saved."""
        mixin._scene = mock_scene

        # Mock layer
        mock_layer = MagicMock()
        mock_layer.id = 1
        mock_layer_class.objects.order_by.return_value.all.return_value = [
            mock_layer
        ]

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.id = 1
        mock_settings_class.objects.filter_by.return_value = [mock_settings]
        mock_settings_class.objects.update = MagicMock()

        # Mock scene item
        mock_item = MagicMock()
        mock_rect = MagicMock()
        mock_rect.width.return_value = 200
        mock_rect.height.return_value = 200
        mock_item.boundingRect.return_value = mock_rect
        mock_scene._layer_items[1] = mock_item

        positions = mixin.recenter_layer_positions()

        # Should have calculated new position and saved to DB
        assert mock_item in positions
        mock_settings_class.objects.update.assert_called_once()


class TestAlignCanvasItemsToViewport:
    """Test align_canvas_items_to_viewport method."""

    def test_align_calculates_center_pos_when_zero(self, mixin, mock_scene):
        """Test that center_pos is calculated when at default (0,0)."""
        mixin._scene = mock_scene
        mixin.center_pos = QPointF(0, 0)
        mixin.update_active_grid_area_position = MagicMock()
        mixin.updateImagePositions = MagicMock()
        mixin.original_item_positions = MagicMock(return_value={})

        mixin.align_canvas_items_to_viewport()

        # center_pos should have been calculated
        assert mixin.center_pos != QPointF(0, 0)

    def test_align_uses_existing_center_pos_when_set(self, mixin, mock_scene):
        """Test that existing center_pos is preserved when non-zero."""
        mixin._scene = mock_scene
        mixin.center_pos = QPointF(150, 250)
        original_center = QPointF(mixin.center_pos)
        mixin.update_active_grid_area_position = MagicMock()
        mixin.updateImagePositions = MagicMock()
        mixin.original_item_positions = MagicMock(return_value={})

        mixin.align_canvas_items_to_viewport()

        # center_pos should be unchanged
        assert int(mixin.center_pos.x()) == int(original_center.x())
        assert int(mixin.center_pos.y()) == int(original_center.y())


class TestUpdateActiveGridAreaPosition:
    """Test update_active_grid_area_position method."""

    def test_update_skips_during_drag(self, mixin, mock_scene):
        """Test that update is skipped when scene is dragging."""
        mixin._scene = mock_scene
        mock_scene.is_dragging = True
        mixin.active_grid_area = MagicMock()

        mixin.update_active_grid_area_position()

        # Position should not have been updated
        mixin.active_grid_area.setPos.assert_not_called()

    def test_update_does_nothing_when_no_active_grid_area(
        self, mixin, mock_scene
    ):
        """Test that update does nothing when active_grid_area is None."""
        mixin._scene = mock_scene
        mixin.active_grid_area = None

        # Should not raise exception
        mixin.update_active_grid_area_position()

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.viewport_positioning_mixin.CanvasPositionManager"
    )
    def test_update_positions_active_grid_area(
        self, mock_manager_class, mixin, mock_scene
    ):
        """Test that active grid area is positioned correctly."""
        mixin._scene = mock_scene
        mixin.active_grid_area = MagicMock()

        # Mock position manager
        manager_instance = MagicMock()
        manager_instance.absolute_to_display.return_value = QPointF(200, 300)
        mock_manager_class.return_value = manager_instance

        mixin.update_active_grid_area_position()

        # Verify position was set
        mixin.active_grid_area.setPos.assert_called_with(QPointF(200, 300))


class TestUpdateImagePositions:
    """Test updateImagePositions method."""

    def test_update_image_positions_calls_scene_method(
        self, mixin, mock_scene
    ):
        """Test that scene.update_image_position is called."""
        mixin._scene = mock_scene
        positions = {MagicMock(): QPointF(10, 20)}

        mixin.updateImagePositions(positions)

        mock_scene.update_image_position.assert_called_once_with(
            mixin.canvas_offset, positions
        )

    def test_update_image_positions_updates_viewport(self, mixin, mock_scene):
        """Test that viewport is updated."""
        mixin._scene = mock_scene

        # Create a mock viewport that persists
        mock_viewport = MagicMock()
        mixin.viewport = MagicMock(return_value=mock_viewport)

        mixin.updateImagePositions()

        # Viewport update should have been called
        mock_viewport.update.assert_called_once()

    def test_update_image_positions_returns_early_if_no_scene(self, mixin):
        """Test that method returns early when scene is None."""
        mixin._scene = None

        mixin.updateImagePositions()

        # Logger should have logged error
        mixin.logger.error.assert_called_once()


class TestApplyViewportCompensation:
    """Test _apply_viewport_compensation method."""

    def test_apply_compensation_adjusts_grid_offset(self, mixin, mock_scene):
        """Test that grid compensation offset is adjusted."""
        mixin._scene = mock_scene
        mixin.update_active_grid_area_position = MagicMock()
        mixin.updateImagePositions = MagicMock()
        original_offset = QPointF(mixin._grid_compensation_offset)

        mixin._apply_viewport_compensation(10, 20)

        # Grid compensation should have been adjusted
        assert mixin._grid_compensation_offset.x() == original_offset.x() + 10
        assert mixin._grid_compensation_offset.y() == original_offset.y() + 20

    def test_apply_compensation_skips_negligible_shifts(
        self, mixin, mock_scene
    ):
        """Test that negligible shifts are ignored."""
        mixin._scene = mock_scene
        original_offset = QPointF(mixin._grid_compensation_offset)

        mixin._apply_viewport_compensation(0.1, 0.2)

        # Offset should be unchanged
        assert mixin._grid_compensation_offset == original_offset

    def test_apply_compensation_returns_early_if_no_scene(self, mixin):
        """Test that method returns early when scene is None."""
        mixin._scene = None
        original_offset = QPointF(mixin._grid_compensation_offset)

        mixin._apply_viewport_compensation(10, 20)

        # Offset should be unchanged
        assert mixin._grid_compensation_offset == original_offset
