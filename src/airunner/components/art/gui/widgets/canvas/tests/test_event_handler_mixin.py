"""Tests for EventHandlerMixin."""

from unittest.mock import MagicMock, Mock, patch
from PySide6.QtCore import QEvent, QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QMouseEvent, QResizeEvent, QKeyEvent
from PySide6.QtWidgets import QGraphicsScene

from airunner.components.art.gui.widgets.canvas.mixins.event_handler_mixin import (
    EventHandlerMixin,
)


class BaseStub:
    """Stub base class providing event methods that mixins call via super()."""

    def wheelEvent(self, event):
        """Stub wheelEvent."""

    def mousePressEvent(self, event):
        """Stub mousePressEvent."""

    def mouseReleaseEvent(self, event):
        """Stub mouseReleaseEvent."""

    def mouseMoveEvent(self, event):
        """Stub mouseMoveEvent."""

    def keyPressEvent(self, event):
        """Stub keyPressEvent."""

    def showEvent(self, event):
        """Stub showEvent."""

    def resizeEvent(self, event):
        """Stub resizeEvent."""

    def enterEvent(self, event):
        """Stub enterEvent."""

    def leaveEvent(self, event):
        """Stub leaveEvent."""


class TestableEventHandlerMixin(EventHandlerMixin, BaseStub):
    """Testable version of EventHandlerMixin with required dependencies."""

    def __init__(self):
        """Initialize testable mixin with mocked dependencies."""
        # Scene mock
        self._scene = MagicMock(spec=QGraphicsScene)

        # State flags
        self._middle_mouse_pressed = False
        self.last_pos = None
        self._initialized = False
        self._is_restoring_state = False
        self._pending_pan_event = False

        # Canvas offset
        self._canvas_offset = QPointF(0, 0)

        # Pan timer
        self._pan_update_timer = Mock(spec=QTimer)
        self._pan_update_timer.isActive = Mock(return_value=False)
        self._pan_update_timer.start = Mock()

        # Viewport tracking
        viewport_mock = Mock()
        viewport_mock.size.return_value = QSize(800, 600)
        self._viewport = viewport_mock
        self._last_viewport_size = QSize(800, 600)

        # Grid compensation
        self._grid_compensation_offset = QPointF(0, 0)

        # Text items
        self._text_items = []
        self._text_item_layer_map = {}

        # Logger
        self.logger = Mock()
        self.logger.info = Mock()
        self.logger.debug = Mock()
        self.logger.exception = Mock()

        # Settings
        self.settings = Mock()
        self.settings.value = Mock(side_effect=lambda key, default: default)

        # API
        self.api = Mock()
        self.api.art.canvas.update_grid_info = Mock()

        # Methods to mock
        self.draw_grid = Mock()
        self.save_canvas_offset = Mock()
        self.load_canvas_offset = Mock()
        self.do_draw = Mock()
        self.toggle_drag_mode = Mock()
        self.set_canvas_color = Mock()
        self.show_active_grid_area = Mock()
        self.align_canvas_items_to_viewport = Mock()
        self.update_active_grid_area_position = Mock()
        self.updateImagePositions = Mock()
        self._apply_viewport_compensation = Mock()
        self._remove_text_item = Mock()

        # Mock super() methods that EventHandlerMixin calls
        self._super_wheelEvent = Mock()
        self._super_mousePressEvent = Mock()
        self._super_mouseReleaseEvent = Mock()
        self._super_mouseMoveEvent = Mock()
        self._super_keyPressEvent = Mock()
        self._super_showEvent = Mock()
        self._super_resizeEvent = Mock()
        self._super_enterEvent = Mock()
        self._super_leaveEvent = Mock()

    @property
    def scene(self):
        """Scene property."""
        return self._scene

    @property
    def canvas_offset(self):
        """Canvas offset property."""
        return self._canvas_offset

    @canvas_offset.setter
    def canvas_offset(self, value):
        """Set canvas offset."""
        self._canvas_offset = value

    @property
    def canvas_offset_x(self):
        """Canvas offset X coordinate."""
        return self._canvas_offset.x()

    @property
    def canvas_offset_y(self):
        """Canvas offset Y coordinate."""
        return self._canvas_offset.y()

    def viewport(self):
        """Return viewport mock."""
        return self._viewport


class TestEventHandlerMixin:
    """Tests for EventHandlerMixin class."""

    def test_wheelEvent_with_ctrl_modifier(self, qapp):
        """Test wheelEvent allows zoom with Ctrl modifier."""
        mixin = TestableEventHandlerMixin()
        event = Mock(spec=QMouseEvent)
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier
        event.ignore = Mock()

        # Don't patch super() - we want our code to execute
        mixin.wheelEvent(event)

        mixin.draw_grid.assert_called_once()
        event.ignore.assert_not_called()

    def test_wheelEvent_without_ctrl_modifier(self, qapp):
        """Test wheelEvent ignores scroll without Ctrl modifier."""
        mixin = TestableEventHandlerMixin()
        event = Mock(spec=QMouseEvent)
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier
        event.ignore = Mock()

        mixin.wheelEvent(event)

        event.ignore.assert_called_once()
        mixin.draw_grid.assert_not_called()

    def test_mousePressEvent_middle_button(self, qapp):
        """Test mousePressEvent handles middle mouse button press."""
        mixin = TestableEventHandlerMixin()
        event = Mock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.MiddleButton
        event.pos.return_value = QPointF(100, 150)
        event.accept = Mock()

        mixin.mousePressEvent(event)

        assert mixin._middle_mouse_pressed is True
        assert mixin.last_pos == QPointF(100, 150)
        event.accept.assert_called_once()

    def test_mousePressEvent_other_button(self, qapp):
        """Test mousePressEvent delegates non-middle button presses."""
        mixin = TestableEventHandlerMixin()
        event = Mock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.LeftButton

        with patch.object(EventHandlerMixin, "mousePressEvent"):
            mixin.mousePressEvent(event)

        assert mixin._middle_mouse_pressed is False

    def test_mouseReleaseEvent_middle_button(self, qapp):
        """Test mouseReleaseEvent handles middle button release."""
        mixin = TestableEventHandlerMixin()
        mixin._middle_mouse_pressed = True
        mixin.last_pos = QPointF(100, 100)
        mixin.scene.handle_cursor = Mock()  # Add handle_cursor to scene mock

        event = Mock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.MiddleButton
        event.accept = Mock()

        mixin.mouseReleaseEvent(event)

        mixin.save_canvas_offset.assert_called_once()
        assert mixin._middle_mouse_pressed is False
        assert mixin.last_pos is None
        event.accept.assert_called_once()

    def test_mouseReleaseEvent_triggers_cursor_update(self, qapp):
        """Test mouseReleaseEvent triggers scene cursor update."""
        mixin = TestableEventHandlerMixin()
        mixin._middle_mouse_pressed = True
        mixin.scene.handle_cursor = Mock()

        event = Mock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.MiddleButton
        event.accept = Mock()

        mixin.mouseReleaseEvent(event)

        mixin.scene.handle_cursor.assert_called_once()

    def test_mouseReleaseEvent_other_button(self, qapp):
        """Test mouseReleaseEvent delegates other button releases."""
        mixin = TestableEventHandlerMixin()
        event = Mock(spec=QMouseEvent)
        event.button.return_value = Qt.MouseButton.LeftButton

        with patch.object(EventHandlerMixin, "mouseReleaseEvent"):
            mixin.mouseReleaseEvent(event)

        mixin.save_canvas_offset.assert_not_called()

    def test_mouseMoveEvent_during_pan(self, qapp):
        """Test mouseMoveEvent handles panning with middle mouse."""
        mixin = TestableEventHandlerMixin()
        mixin._middle_mouse_pressed = True
        mixin.last_pos = QPointF(100, 100)
        mixin.canvas_offset = QPointF(50, 50)

        event = Mock()
        event.pos.return_value = QPointF(110, 105)
        event.accept = Mock()

        mixin.mouseMoveEvent(event)

        # Delta is (110-100, 105-100) = (10, 5)
        # New offset should be (50-10, 50-5) = (40, 45)
        assert mixin.canvas_offset == QPointF(40, 45)
        assert mixin.last_pos == QPointF(110, 105)
        mixin.api.art.canvas.update_grid_info.assert_called_once()
        mixin._pan_update_timer.start.assert_called_once_with(1)
        event.accept.assert_called_once()

    def test_mouseMoveEvent_during_active_pan_timer(self, qapp):
        """Test mouseMoveEvent sets pending flag when pan timer active."""
        mixin = TestableEventHandlerMixin()
        mixin._middle_mouse_pressed = True
        mixin.last_pos = QPointF(100, 100)
        mixin._pan_update_timer.isActive = Mock(return_value=True)

        event = Mock()
        event.pos.return_value = QPointF(105, 105)
        event.accept = Mock()

        mixin.mouseMoveEvent(event)

        assert mixin._pending_pan_event is True
        # Should not start timer again
        mixin._pan_update_timer.start.assert_not_called()

    def test_mouseMoveEvent_without_pan(self, qapp):
        """Test mouseMoveEvent delegates when not panning."""
        mixin = TestableEventHandlerMixin()
        mixin._middle_mouse_pressed = False
        event = Mock()

        with patch.object(EventHandlerMixin, "mouseMoveEvent"):
            mixin.mouseMoveEvent(event)

        mixin.api.art.canvas.update_grid_info.assert_not_called()

    def test_keyPressEvent_delete_key_with_selected_text(self, qapp):
        """Test keyPressEvent deletes selected text items."""
        mixin = TestableEventHandlerMixin()

        # Create mock text items
        selected_item = Mock()
        selected_item.isSelected.return_value = True
        unselected_item = Mock()
        unselected_item.isSelected.return_value = False

        mixin._text_items = [selected_item, unselected_item]
        mixin._text_item_layer_map = {selected_item: 1, unselected_item: 2}
        mixin.scene._history_transactions = {}
        mixin.scene._begin_layer_history_transaction = Mock()
        mixin.scene._commit_layer_history_transaction = Mock()

        event = Mock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_Delete

        mixin.keyPressEvent(event)

        # Should remove only selected item
        mixin._remove_text_item.assert_called_once_with(
            selected_item, manage_transaction=False
        )
        mixin.scene._begin_layer_history_transaction.assert_called_once_with(
            1, "text"
        )
        mixin.scene._commit_layer_history_transaction.assert_called_once_with(
            1, "text"
        )

    def test_keyPressEvent_delete_key_no_selection(self, qapp):
        """Test keyPressEvent with Delete but no selected items."""
        mixin = TestableEventHandlerMixin()
        mixin._text_items = []

        event = Mock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_Delete

        with patch.object(EventHandlerMixin, "keyPressEvent"):
            mixin.keyPressEvent(event)

        mixin._remove_text_item.assert_not_called()

    def test_keyPressEvent_other_key(self, qapp):
        """Test keyPressEvent delegates non-Delete keys."""
        mixin = TestableEventHandlerMixin()
        event = Mock(spec=QKeyEvent)
        event.key.return_value = Qt.Key.Key_A

        with patch.object(EventHandlerMixin, "keyPressEvent"):
            mixin.keyPressEvent(event)

        mixin._remove_text_item.assert_not_called()

    def test_do_pan_update(self, qapp):
        """Test _do_pan_update refreshes positions and grid."""
        mixin = TestableEventHandlerMixin()

        mixin._do_pan_update()

        mixin.update_active_grid_area_position.assert_called_once()
        mixin.updateImagePositions.assert_called_once()
        mixin.draw_grid.assert_called_once()

    def test_do_pan_update_with_pending_event(self, qapp):
        """Test _do_pan_update restarts timer when pending event exists."""
        mixin = TestableEventHandlerMixin()
        mixin._pending_pan_event = True

        mixin._do_pan_update()

        assert mixin._pending_pan_event is False
        mixin._pan_update_timer.start.assert_called_once_with(1)

    def test_showEvent_first_show(self, qapp):
        """Test showEvent initializes canvas on first show."""
        mixin = TestableEventHandlerMixin()
        mixin._initialized = False
        mixin.scene.original_item_positions = {}
        mixin.scene._refresh_layer_display = Mock()
        mixin.scene.show_event = Mock()

        # Mock QTimer.singleShot to execute callback immediately
        with patch(
            "airunner.components.art.gui.widgets.canvas.mixins.event_handler_mixin.QTimer.singleShot",
            side_effect=lambda delay, func: func(),
        ):
            event = Mock(spec=QEvent)
            # Don't patch super() - let showEvent execute
            mixin.showEvent(event)

        assert mixin._initialized is True
        mixin.load_canvas_offset.assert_called_once()
        mixin.do_draw.assert_called_once_with(True)
        mixin.toggle_drag_mode.assert_called_once()
        mixin.set_canvas_color.assert_called_once_with(mixin.scene)
        mixin.show_active_grid_area.assert_called_once()
        mixin.scene._refresh_layer_display.assert_called_once()
        mixin.align_canvas_items_to_viewport.assert_called_once()

    def test_showEvent_subsequent_show_no_resize(self, qapp):
        """Test showEvent on subsequent show with unchanged viewport."""
        mixin = TestableEventHandlerMixin()
        mixin._initialized = True
        mixin._last_viewport_size = QSize(800, 600)
        mixin._viewport.size.return_value = QSize(800, 600)

        event = Mock(spec=QEvent)
        with patch.object(EventHandlerMixin, "showEvent"):
            mixin.showEvent(event)

        mixin._apply_viewport_compensation.assert_not_called()
        mixin.draw_grid.assert_not_called()

    def test_showEvent_subsequent_show_with_resize(self, qapp):
        """Test showEvent compensates for viewport size change while hidden."""
        mixin = TestableEventHandlerMixin()
        mixin._initialized = True
        mixin._is_restoring_state = False
        mixin._last_viewport_size = QSize(800, 600)
        mixin._viewport.size.return_value = QSize(1000, 700)

        event = Mock(spec=QEvent)
        # Don't patch super() - let showEvent execute
        mixin.showEvent(event)

        # New center: (500, 350), old center: (400, 300)
        # Shift: (100, 50)
        mixin._apply_viewport_compensation.assert_called_once_with(100.0, 50.0)
        mixin.draw_grid.assert_called_once()
        assert mixin._last_viewport_size == QSize(1000, 700)

    def test_finish_state_restoration(self, qapp):
        """Test _finish_state_restoration completes initialization."""
        mixin = TestableEventHandlerMixin()
        mixin._is_restoring_state = True
        mixin.settings.value = Mock(
            side_effect=lambda key, default: 10.0 if "x" in key else 20.0
        )
        mixin.scene.show_event = Mock()

        mixin._finish_state_restoration()

        assert mixin._is_restoring_state is False
        assert mixin.canvas_offset == QPointF(10.0, 20.0)
        mixin.update_active_grid_area_position.assert_called_once()
        mixin.updateImagePositions.assert_called_once()
        mixin.scene.show_event.assert_called_once()

    def test_resizeEvent_during_restoration(self, qapp):
        """Test resizeEvent skips compensation during state restoration."""
        mixin = TestableEventHandlerMixin()
        mixin._is_restoring_state = True
        mixin._initialized = False

        event = Mock(spec=QResizeEvent)
        with patch.object(EventHandlerMixin, "resizeEvent"):
            mixin.resizeEvent(event)

        mixin._apply_viewport_compensation.assert_not_called()
        mixin.draw_grid.assert_not_called()

    def test_resizeEvent_after_initialization(self, qapp):
        """Test resizeEvent applies compensation after initialization."""
        mixin = TestableEventHandlerMixin()
        mixin._is_restoring_state = False
        mixin._initialized = True
        mixin._last_viewport_size = QSize(800, 600)
        mixin._viewport.size.return_value = QSize(1000, 700)

        event = Mock(spec=QResizeEvent)
        # Don't patch super() - let resizeEvent execute
        mixin.resizeEvent(event)

        # New center: (500, 350), old center: (400, 300)
        # Shift: (100, 50)
        mixin._apply_viewport_compensation.assert_called_once_with(100.0, 50.0)
        mixin.draw_grid.assert_called_once()
        assert mixin._last_viewport_size == QSize(1000, 700)

    def test_resizeEvent_no_size_change(self, qapp):
        """Test resizeEvent skips compensation when size unchanged."""
        mixin = TestableEventHandlerMixin()
        mixin._is_restoring_state = False
        mixin._initialized = True
        mixin._last_viewport_size = QSize(800, 600)
        mixin._viewport.size.return_value = QSize(800, 600)

        event = Mock(spec=QResizeEvent)
        with patch.object(EventHandlerMixin, "resizeEvent"):
            mixin.resizeEvent(event)

        mixin._apply_viewport_compensation.assert_not_called()
        mixin.draw_grid.assert_not_called()

    def test_enterEvent(self, qapp):
        """Test enterEvent delegates to scene."""
        mixin = TestableEventHandlerMixin()
        mixin.scene.enterEvent = Mock()

        event = Mock(spec=QEvent)
        # Don't patch super() - let enterEvent execute
        mixin.enterEvent(event)

        mixin.scene.enterEvent.assert_called_once_with(event)

    def test_leaveEvent(self, qapp):
        """Test leaveEvent delegates to scene."""
        mixin = TestableEventHandlerMixin()
        mixin.scene.leaveEvent = Mock()

        event = Mock(spec=QEvent)
        # Don't patch super() - let leaveEvent execute
        mixin.leaveEvent(event)

        mixin.scene.leaveEvent.assert_called_once_with(event)
