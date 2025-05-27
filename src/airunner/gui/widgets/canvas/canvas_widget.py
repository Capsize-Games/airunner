import logging
from typing import Optional, Dict

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication  # ADDED QApplication

from airunner.gui.cursors.circle_brush import circle_cursor
from airunner.enums import SignalCode, CanvasToolName
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.canvas.templates.canvas_ui import Ui_canvas
from airunner.utils.application import set_widget_state
from airunner.utils.widgets import load_splitter_settings
from airunner.gui.widgets.canvas.logic.canvas_logic import CanvasLogic


class CanvasWidget(BaseWidget):
    """Widget responsible for canvas drawing and grid management.

    This widget provides the main canvas interface for AI Runner, allowing users to:
    - Draw on a canvas using brush and eraser tools
    - Display and manipulate the grid system
    - Import/export images
    - Handle the active grid area for positioning

    Attributes:
        widget_class_: The UI template class for this widget.
        icons: List of icon definitions for toolbar buttons.
        drawing_pad_image_changed: Signal emitted when the canvas image is updated.
    """

    widget_class_ = Ui_canvas
    icons = [
        ("file-plus", "new_button"),
        ("folder", "import_button"),
        ("save", "export_button"),
        ("target", "recenter_button"),
        ("object-selected-icon", "active_grid_area_button"),
        ("pencil-icon", "brush_button"),
        ("eraser-icon", "eraser_button"),
        ("grid", "grid_button"),
        ("corner-up-left", "undo_button"),
        ("corner-up-right", "redo_button"),
        ("type", "text_button"),
    ]

    drawing_pad_image_changed = Signal()

    def __init__(self, *args, logic=None, **kwargs):
        """Initialize the CanvasWidget.

        Args:
            *args: Variable length argument list passed to parent classes.
            logic: Optional CanvasLogic instance. If None, a new instance will be created.
            **kwargs: Arbitrary keyword arguments passed to parent classes.
        """
        self._logger = logging.getLogger("airunner.canvas_widget")
        self._logger.debug("CanvasWidget __init__ called")
        self.signal_handlers = {
            SignalCode.ENABLE_BRUSH_TOOL_SIGNAL: lambda _message: self.on_brush_button_toggled(
                True
            ),
            SignalCode.ENABLE_ERASER_TOOL_SIGNAL: lambda _message: self.on_eraser_button_toggled(
                True
            ),
            SignalCode.ENABLE_MOVE_TOOL_SIGNAL: lambda _message: self.on_active_grid_area_button_toggled(
                True
            ),
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL: self.on_toggle_tool_signal,
            SignalCode.TOGGLE_TOOL: self.on_toggle_tool_signal,
            SignalCode.TOGGLE_GRID: self.on_toggle_grid_signal,
            SignalCode.CANVAS_UPDATE_CURSOR: self.on_canvas_update_cursor_signal,
        }
        super().__init__(*args, **kwargs)

        if logic is not None:
            self.logic = logic
        else:
            self.logic = CanvasLogic(
                self.application_settings, self.update_application_settings
            )

        # Configure default splitter sizes for canvas_splitter
        # Assuming the main canvas area is the second panel (index 1)
        default_canvas_splitter_config = {
            "canvas_splitter": {"index_to_maximize": 1, "min_other_size": 50}
        }
        load_splitter_settings(
            self.ui,
            self._splitters,  # self._splitters is ["canvas_splitter"]
            default_maximize_config=default_canvas_splitter_config,
        )

        current_tool = self.current_tool
        show_grid = self.grid_settings.show_grid

        self._startPos = QPoint(0, 0)
        self.images = {}
        self.active_grid_area_pivot_point = QPoint(0, 0)
        self.active_grid_area_position = QPoint(0, 0)
        self.current_image_index = 0
        self.draggable_pixmaps_in_scene = {}
        self.drag_pos: QPoint = Optional[None]
        self._grid_settings = {}
        self._active_grid_settings = {}

        self.ui.grid_button.blockSignals(True)
        self.ui.grid_button.setChecked(show_grid)
        self.ui.grid_button.blockSignals(False)

        set_widget_state(
            self.ui.grid_button,
            current_tool is CanvasToolName.ACTIVE_GRID_AREA,
        )
        set_widget_state(self.ui.brush_button, current_tool is CanvasToolName.BRUSH)
        set_widget_state(self.ui.eraser_button, current_tool is CanvasToolName.ERASER)
        set_widget_state(self.ui.text_button, current_tool is CanvasToolName.TEXT)
        set_widget_state(self.ui.grid_button, show_grid is True)

        # Connect CANVAS_IMAGE_UPDATED_SIGNAL to emit drawing_pad_image_changed
        self.register(
            SignalCode.CANVAS_IMAGE_UPDATED_SIGNAL,
            self._on_canvas_image_updated_signal,
        )

    @property
    def current_tool(self):
        """Get the currently active canvas tool.

        Returns:
            CanvasToolName: The current tool being used, or None if no tool is active.
        """
        return self.logic.current_tool

    @property
    def image_pivot_point(self):
        """Get the current image pivot point.

        Returns:
            QPoint: The current pivot point coordinates for image positioning.
        """
        return self.logic.image_pivot_point

    @image_pivot_point.setter
    def image_pivot_point(self, value):
        """Set the image pivot point.

        Args:
            value (QPoint): The new pivot point coordinates.
        """
        self.logic.image_pivot_point = value

    @Slot(bool)
    def on_text_button_toggled(self, val: bool):
        self.api.art.canvas.toggle_tool(CanvasToolName.TEXT, val)

    @Slot()
    def on_recenter_button_clicked(self):
        self.api.art.canvas.recenter_grid()

    @Slot()
    def on_new_button_clicked(self):
        self._logger.debug("on_new_button_clicked: clearing canvas")
        self.api.art.canvas.clear()
        self._logger.debug("Emitting drawing_pad_image_changed signal from clear")
        self.api.art.canvas.drawing_pad_image_changed()

    @Slot()
    def on_import_button_clicked(self):
        self._logger.debug("on_import_button_clicked: importing image")
        self.api.art.canvas.import_image()
        self._logger.debug("Emitting drawing_pad_image_changed signal from import")
        self.api.art.canvas.drawing_pad_image_changed()

    @Slot()
    def on_export_button_clicked(self):
        self.api.art.canvas.export_image()

    @Slot()
    def on_undo_button_clicked(self):
        self._logger.debug("on_undo_button_clicked: undo")
        self.api.art.canvas.undo()
        self._logger.debug("Emitting drawing_pad_image_changed signal from undo")
        self.api.art.canvas.drawing_pad_image_changed()

    @Slot()
    def on_redo_button_clicked(self):
        self._logger.debug("on_redo_button_clicked: redo")
        self.api.art.canvas.redo()
        self._logger.debug("Emitting drawing_pad_image_changed signal from redo")
        self.api.art.canvas.drawing_pad_image_changed()

    @Slot(bool)
    def on_grid_button_toggled(self, val: bool):
        self.logic.set_grid(self.grid_settings, val)

    @Slot(bool)
    def on_brush_button_toggled(self, val: bool):
        self.logic.set_tool(CanvasToolName.BRUSH, val)

    @Slot(bool)
    def on_eraser_button_toggled(self, val: bool):
        self.logic.set_tool(CanvasToolName.ERASER, val)

    @Slot(bool)
    def on_active_grid_area_button_toggled(self, val: bool):
        self.logic.set_tool(CanvasToolName.ACTIVE_GRID_AREA, val)

    def on_toggle_tool_signal(self, message: Dict):
        """Handle tool toggle signal from the application.

        Args:
            message (Dict): Signal message containing 'tool' and 'active' keys.
        """
        tool = message.get("tool", None)
        active = message.get("active", False)
        self.logic.set_tool(tool, active)
        self._update_action_buttons(tool, active)
        self._update_cursor()

    def on_toggle_grid_signal(self, message: Dict):
        """Handle grid toggle signal from the application.

        Args:
            message (Dict): Signal message containing 'show_grid' key.
        """
        self.logic.set_grid(self.grid_settings, message.get("show_grid", True))
        self.ui.grid_button.setChecked(message.get("show_grid", True))

    def _update_action_buttons(self, tool, active):
        """Update the visual state of action buttons based on current tool.

        Args:
            tool: The currently active tool.
            active (bool): Whether the tool is active.
        """
        self.logic.update_action_buttons(self.ui, self.grid_settings, tool, active)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._default_splitter_settings_applied and self.isVisible():
            self._apply_default_splitter_settings()
            self._default_splitter_settings_applied = True

        if not self._initialized:
            self._initialized = True
            self._update_cursor()

    def on_canvas_update_cursor_signal(self, message: Dict):
        self._update_cursor(message)

    def _apply_default_splitter_settings(self):
        """
        Applies default splitter sizes. Called to ensure
        widget geometry is more likely to be initialized.
        """
        if hasattr(self, "ui") and self.ui is not None:
            QApplication.processEvents()  # Ensure pending layout events are processed
            default_canvas_splitter_config = {
                "canvas_splitter": {
                    "index_to_maximize": 1,
                    "min_other_size": 50,
                }
            }
            load_splitter_settings(
                self.ui,
                self._splitters,  # Uses self._splitters defined in __init__
                default_maximize_config=default_canvas_splitter_config,
            )
        else:
            # This case should ideally not happen if __init__ completed successfully.
            # Consider logging if a logger is available and configured for this class.
            print(
                f"Error in CanvasWidget: UI not available when attempting to apply default splitter settings."
            )

    def _update_cursor(self, message: Optional[Dict] = None):
        message = message or {}
        event = message.get("event", None)
        current_tool = message.get("current_tool", self.current_tool)
        brush_size = getattr(self, "brush_settings", None)
        brush_size = brush_size.size if brush_size else 32
        apply_cursor = message.get("apply_cursor", False)
        cursor_type = self.logic.get_cursor_type(
            current_tool, event, brush_size, apply_cursor
        )
        # Map cursor_type string to actual QCursor or value
        if cursor_type == "circle_brush":
            # Use white outline and transparent fill for brush/eraser cursor
            cursor = circle_cursor(
                Qt.GlobalColor.white, Qt.GlobalColor.transparent, brush_size
            )
        elif cursor_type == "closed_hand":
            cursor = Qt.CursorShape.ClosedHandCursor
        elif cursor_type == "open_hand":
            cursor = Qt.CursorShape.OpenHandCursor
        elif cursor_type == "arrow":
            cursor = Qt.CursorShape.ArrowCursor
        else:
            cursor = Qt.CursorShape.ArrowCursor
        # Special handling for ACTIVE_GRID_AREA with event.buttons() == Qt.MouseButton.LeftButton
        if (
            current_tool is not None
            and hasattr(event, "buttons")
            and callable(event.buttons)
            and current_tool == CanvasToolName.ACTIVE_GRID_AREA
            and event.buttons() == Qt.MouseButton.LeftButton
        ):
            cursor = Qt.CursorShape.ClosedHandCursor
        elif (
            current_tool is not None
            and hasattr(event, "buttons")
            and callable(event.buttons)
            and current_tool == CanvasToolName.ACTIVE_GRID_AREA
            and event.buttons() != Qt.MouseButton.LeftButton
        ):
            cursor = Qt.CursorShape.OpenHandCursor
        if not hasattr(self, "_current_cursor") or self._current_cursor != cursor:
            if cursor is not None:
                self.setCursor(cursor)
            self._current_cursor = cursor

    def toggle_grid(self, _val):
        self.do_draw()

    def do_draw(self, force_draw: bool = False):
        """Execute a drawing operation on the canvas.

        Args:
            force_draw (bool): Whether to force a redraw even if no changes are detected.
        """
        self._logger.debug(f"do_draw called, force_draw={force_draw}")
        self.api.art.canvas.do_draw(force_draw)
        self.ui.canvas_container_size = self.ui.canvas_container.viewport().size()
        self._logger.debug("Emitting drawing_pad_image_changed signal from do_draw")
        self.api.art.canvas.drawing_pad_image_changed()

    def _on_canvas_image_updated_signal(self, *args, **kwargs):
        """Handle canvas image updated signal.

        This method is called when the canvas image is updated and emits
        the drawing_pad_image_changed signal to notify other components.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        self._logger.debug(
            "_on_canvas_image_updated_signal: emitting drawing_pad_image_changed"
        )
        self.api.art.canvas.drawing_pad_image_changed()
