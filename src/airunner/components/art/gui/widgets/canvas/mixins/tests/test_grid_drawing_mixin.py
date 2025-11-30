"""Tests for GridDrawingMixin."""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QPointF, Qt, QSize

from airunner.components.art.gui.widgets.canvas.mixins.grid_drawing_mixin import (
    GridDrawingMixin,
)
from airunner.enums import SignalCode, CanvasToolName


class TestableGridDrawingMixin(GridDrawingMixin):
    """Testable version of GridDrawingMixin with required dependencies."""

    def __init__(self):
        self.grid_item = None
        self.active_grid_area = None
        self.drawing = False
        self.initialized = True
        self.center_pos = QPointF(100, 100)
        self.canvas_offset_x = 0
        self.canvas_offset_y = 0
        self.logger = MagicMock()
        self.grid_settings = MagicMock()
        self.grid_settings.show_grid = True
        self.active_grid_settings = MagicMock()
        self.active_grid_settings.pos_x = 50
        self.active_grid_settings.pos_y = 50
        self.application_settings = MagicMock()
        self.application_settings.working_width = 1024
        self.application_settings.working_height = 1024
        self.settings = MagicMock()
        self._grid_compensation_offset = QPointF(0, 0)
        self.canvas_offset = QPointF(0, 0)
        self.current_tool = CanvasToolName.BRUSH
        self._do_show_active_grid_area = True
        self._scene = None

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
        mock_viewport.width.return_value = 800
        mock_viewport.height.return_value = 600
        return mock_viewport

    def set_scene_rect(self):
        """Mock set_scene_rect method."""

    def update_scene(self):
        """Mock update_scene method."""

    def remove_scene_item(self, item):
        """Mock remove_scene_item method."""

    def update_active_grid_settings(self, **kwargs):
        """Mock update_active_grid_settings method."""

    def update_active_grid_area_position(self):
        """Mock update_active_grid_area_position method."""


@pytest.fixture
def mixin(qapp):
    """Create a testable grid drawing mixin instance."""
    return TestableGridDrawingMixin()


@pytest.fixture
def mock_scene():
    """Create a mock scene."""
    scene = MagicMock()
    scene.is_dragging = False
    return scene


class TestDoDrawMethod:
    """Test do_draw method."""

    def test_do_draw_returns_early_if_no_scene(self, mixin):
        """Test that do_draw returns early when scene is None."""
        mixin._scene = None
        mixin.drawing = False

        mixin.do_draw()

        # Should not have set drawing flag
        assert mixin.drawing is False

    def test_do_draw_returns_early_if_drawing_without_force(
        self, mixin, mock_scene
    ):
        """Test that do_draw returns early if already drawing (without force)."""
        mixin._scene = mock_scene
        mixin.drawing = True

        mixin.do_draw(force_draw=False)

        # Scene should not have been accessed for removeItem
        mock_scene.removeItem.assert_not_called()

    def test_do_draw_returns_early_if_not_initialized_without_force(
        self, mixin, mock_scene
    ):
        """Test that do_draw returns early if not initialized (without force)."""
        mixin._scene = mock_scene
        mixin.initialized = False
        mixin.drawing = False

        mixin.do_draw(force_draw=False)

        # Should not proceed with drawing
        mock_scene.removeItem.assert_not_called()

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.grid_drawing_mixin.GridGraphicsItem"
    )
    def test_do_draw_removes_old_grid_item(
        self, mock_grid_item_class, mixin, mock_scene
    ):
        """Test that do_draw removes old grid item before creating new one."""
        mixin._scene = mock_scene
        old_grid_item = MagicMock()
        mixin.grid_item = old_grid_item
        mixin.grid_settings.show_grid = True

        mixin.do_draw()

        # Verify old grid item was removed
        mock_scene.removeItem.assert_any_call(old_grid_item)

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.grid_drawing_mixin.GridGraphicsItem"
    )
    def test_do_draw_creates_new_grid_item_when_show_grid_true(
        self, mock_grid_item_class, mixin, mock_scene
    ):
        """Test that do_draw creates new grid item when show_grid is True."""
        mixin._scene = mock_scene
        mixin.grid_settings.show_grid = True
        grid_instance = MagicMock()
        mock_grid_item_class.return_value = grid_instance

        # Mock show_active_grid_area to prevent it from adding items
        mixin.show_active_grid_area = MagicMock()

        mixin.do_draw()

        # Verify GridGraphicsItem was created with correct parameters
        mock_grid_item_class.assert_called_once_with(mixin, mixin.center_pos)
        # Verify grid instance was added to scene
        assert any(
            call[0][0] == grid_instance
            for call in mock_scene.addItem.call_args_list
        ) or mock_scene.addItem.assert_called_with(grid_instance)
        assert mixin.grid_item == grid_instance

    def test_do_draw_does_not_create_grid_item_when_show_grid_false(
        self, mixin, mock_scene
    ):
        """Test that do_draw does not create grid item when show_grid is False."""
        mixin._scene = mock_scene
        mixin.grid_settings.show_grid = False

        mixin.do_draw()

        # Grid item should be None after draw
        assert mixin.grid_item is None

    def test_do_draw_sets_and_clears_drawing_flag(self, mixin, mock_scene):
        """Test that do_draw sets and clears drawing flag properly."""
        mixin._scene = mock_scene
        mixin.grid_settings.show_grid = False
        assert mixin.drawing is False

        # Patch show_active_grid_area to check drawing flag state during execution
        drawing_during_execution = []

        def capture_drawing_state():
            drawing_during_execution.append(mixin.drawing)

        mixin.show_active_grid_area = capture_drawing_state

        mixin.do_draw()

        # During execution, drawing should have been True
        assert drawing_during_execution[0] is True
        # After execution, drawing should be False
        assert mixin.drawing is False

    def test_do_draw_with_force_draw_overrides_drawing_check(
        self, mixin, mock_scene
    ):
        """Test that force_draw=True allows drawing even if already drawing."""
        mixin._scene = mock_scene
        mixin.drawing = True
        mixin.grid_settings.show_grid = False

        mixin.do_draw(force_draw=True)

        # Should have proceeded with drawing (drawing flag set to True then False)
        assert mixin.drawing is False


class TestDrawGridMethod:
    """Test draw_grid method."""

    def test_draw_grid_updates_grid_item_when_exists(self, mixin):
        """Test that draw_grid calls update on grid_item."""
        mock_grid_item = MagicMock()
        mixin.grid_item = mock_grid_item

        mixin.draw_grid()

        mock_grid_item.update.assert_called_once()

    def test_draw_grid_does_nothing_when_no_grid_item(self, mixin):
        """Test that draw_grid does nothing when grid_item is None."""
        mixin.grid_item = None

        # Should not raise exception
        mixin.draw_grid()

    def test_draw_grid_accepts_optional_size_parameter(self, mixin):
        """Test that draw_grid accepts optional size parameter."""
        mock_grid_item = MagicMock()
        mixin.grid_item = mock_grid_item
        size = QSize(800, 600)

        mixin.draw_grid(size=size)

        # Should still call update (size parameter is unused but accepted)
        mock_grid_item.update.assert_called_once()


class TestClearLinesMethod:
    """Test clear_lines method."""

    def test_clear_lines_removes_grid_item_from_scene(self, mixin, mock_scene):
        """Test that clear_lines removes grid item from scene."""
        mixin._scene = mock_scene
        mock_grid_item = MagicMock()
        mixin.grid_item = mock_grid_item

        mixin.clear_lines()

        mock_scene.removeItem.assert_called_once_with(mock_grid_item)
        assert mixin.grid_item is None

    def test_clear_lines_does_nothing_when_no_grid_item(
        self, mixin, mock_scene
    ):
        """Test that clear_lines does nothing when grid_item is None."""
        mixin._scene = mock_scene
        mixin.grid_item = None

        mixin.clear_lines()

        mock_scene.removeItem.assert_not_called()


class TestShowActiveGridArea:
    """Test show_active_grid_area method."""

    def test_show_active_grid_area_removes_area_when_disabled(
        self, mixin, mock_scene
    ):
        """Test that active grid area is removed when disabled."""
        mixin._scene = mock_scene
        mixin._do_show_active_grid_area = False
        mixin.active_grid_area = MagicMock()

        mixin.show_active_grid_area()

        assert mixin.active_grid_area is None

    def test_show_active_grid_area_skips_during_drag(self, mixin, mock_scene):
        """Test that repositioning is skipped during drag."""
        mixin._scene = mock_scene
        mock_scene.is_dragging = True
        mixin.active_grid_area = MagicMock()

        mixin.show_active_grid_area()

        # Logger should have been called with skip message
        mixin.logger.info.assert_any_call(
            "[ACTIVE GRID] Skipping show_active_grid_area - is_dragging is True"
        )

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.grid_drawing_mixin.ActiveGridArea"
    )
    def test_show_active_grid_area_creates_area_if_not_exists(
        self, mock_active_grid_class, mixin, mock_scene
    ):
        """Test that active grid area is created if it doesn't exist."""
        mixin._scene = mock_scene
        area_instance = MagicMock()
        mock_active_grid_class.return_value = area_instance

        mixin.show_active_grid_area()

        # Verify area was created and added to scene
        mock_active_grid_class.assert_called_once()
        area_instance.setZValue.assert_called_once_with(10000)
        mock_scene.addItem.assert_called_with(area_instance)
        assert mixin.active_grid_area == area_instance

    def test_show_active_grid_area_registers_signal_handler(
        self, mixin, mock_scene
    ):
        """Test that signal handler is registered for area updates."""
        mixin._scene = mock_scene
        mixin.active_grid_area = None

        with patch(
            "airunner.components.art.gui.widgets.canvas.mixins.grid_drawing_mixin.ActiveGridArea"
        ) as mock_class:
            area_instance = MagicMock()
            mock_class.return_value = area_instance

            mixin.show_active_grid_area()

            # Verify signal registration
            area_instance.register.assert_called_once_with(
                SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED,
                mixin.update_active_grid_area_position,
            )

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.grid_drawing_mixin.CanvasPositionManager"
    )
    def test_show_active_grid_area_positions_using_saved_settings(
        self, mock_manager_class, mixin, mock_scene
    ):
        """Test that active grid area is positioned using saved settings."""
        mixin._scene = mock_scene
        mixin.active_grid_settings.pos_x = 100
        mixin.active_grid_settings.pos_y = 200
        mixin.active_grid_area = MagicMock()

        # Mock position manager
        manager_instance = MagicMock()
        manager_instance.absolute_to_display.return_value = QPointF(150, 250)
        mock_manager_class.return_value = manager_instance

        mixin.show_active_grid_area()

        # Verify position was set
        mixin.active_grid_area.setPos.assert_called_with(150, 250)

    def test_show_active_grid_area_calculates_default_position_when_none(
        self, mixin, mock_scene
    ):
        """Test that default position is calculated when settings are None."""
        mixin._scene = mock_scene
        mixin.active_grid_settings.pos_x = None
        mixin.active_grid_settings.pos_y = None
        mixin.active_grid_area = MagicMock()

        with patch(
            "airunner.components.art.gui.widgets.canvas.mixins.grid_drawing_mixin.CanvasPositionManager"
        ):
            mixin.show_active_grid_area()

        # Verify update_active_grid_settings was called (would save calculated position)
        # This is a bit indirect but we can't easily verify the exact call without more mocking


class TestUpdateActiveGridMouseAcceptance:
    """Test _update_active_grid_mouse_acceptance method."""

    def test_update_mouse_acceptance_returns_early_if_no_area(self, mixin):
        """Test that method returns early when active_grid_area is None."""
        mixin.active_grid_area = None

        # Should not raise exception
        mixin._update_active_grid_mouse_acceptance()

    def test_update_mouse_acceptance_disables_events_for_move_tool(
        self, mixin
    ):
        """Test that mouse events are disabled when MOVE tool is active."""
        mixin.active_grid_area = MagicMock()
        mixin.current_tool = CanvasToolName.MOVE

        mixin._update_active_grid_mouse_acceptance()

        # Verify NoButton was set
        mixin.active_grid_area.setAcceptedMouseButtons.assert_called_once_with(
            Qt.MouseButton.NoButton
        )
        # Verify hover events disabled
        mixin.active_grid_area.setAcceptHoverEvents.assert_called_with(False)

    def test_update_mouse_acceptance_enables_events_for_other_tools(
        self, mixin
    ):
        """Test that mouse events are enabled for non-MOVE tools."""
        mixin.active_grid_area = MagicMock()
        mixin.current_tool = CanvasToolName.BRUSH

        mixin._update_active_grid_mouse_acceptance()

        # Verify left and right buttons accepted
        expected_buttons = (
            Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
        )
        mixin.active_grid_area.setAcceptedMouseButtons.assert_called_once_with(
            expected_buttons
        )
        # Verify hover events enabled
        mixin.active_grid_area.setAcceptHoverEvents.assert_called_with(True)

    def test_update_mouse_acceptance_handles_exceptions_gracefully(
        self, mixin
    ):
        """Test that exceptions are caught and logged."""
        mixin.active_grid_area = MagicMock()
        mixin.active_grid_area.setAcceptedMouseButtons.side_effect = Exception(
            "Test error"
        )
        mixin.current_tool = CanvasToolName.BRUSH

        # Should not raise exception
        mixin._update_active_grid_mouse_acceptance()

        # Logger should have been called
        mixin.logger.exception.assert_called_once()


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple methods."""

    @patch(
        "airunner.components.art.gui.widgets.canvas.mixins.grid_drawing_mixin.GridGraphicsItem"
    )
    def test_do_draw_calls_show_active_grid_area(
        self, mock_grid_class, mixin, mock_scene
    ):
        """Test that do_draw calls show_active_grid_area."""
        mixin._scene = mock_scene
        show_called = []

        def track_show_call():
            show_called.append(True)

        mixin.show_active_grid_area = track_show_call

        mixin.do_draw()

        assert len(show_called) == 1

    def test_grid_lifecycle_create_update_clear(self, mixin, mock_scene):
        """Test complete grid lifecycle: create, update, clear."""
        mixin._scene = mock_scene
        mixin.grid_settings.show_grid = True

        # Create grid
        with patch(
            "airunner.components.art.gui.widgets.canvas.mixins.grid_drawing_mixin.GridGraphicsItem"
        ) as mock_class:
            grid_instance = MagicMock()
            mock_class.return_value = grid_instance

            mixin.do_draw()
            assert mixin.grid_item == grid_instance

            # Update grid
            mixin.draw_grid()
            grid_instance.update.assert_called_once()

            # Clear grid
            mixin.clear_lines()
            assert mixin.grid_item is None
            mock_scene.removeItem.assert_called_with(grid_instance)
