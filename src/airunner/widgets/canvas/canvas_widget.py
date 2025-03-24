from typing import Optional

from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtCore import Slot

from airunner.cursors.circle_brush import circle_cursor
from airunner.enums import SignalCode, CanvasToolName
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.canvas.templates.canvas_ui import Ui_canvas
from airunner.utils import set_widget_state


class CanvasWidget(
    BaseWidget
):
    """
    Widget responsible for multiple functionalities:

    - Allows the user to draw on a canvas.
    - Displays the grid.
    - Displays images.
    - Handles the active grid area.
    """
    widget_class_ = Ui_canvas
    icons = [
        ("circle-center-icon", "recenter_Grid_Button"),
        ("object-selected-icon", "actionToggle_Active_Grid_Area"),
        ("pencil-icon", "actionToggle_Brush"),
        ("eraser-icon", "actionToggle_Eraser"),
        ("frame-grid-icon", "actionToggle_Grid"),
        ("layer-icon", "actionMask_toggle"),
    ]

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.ENABLE_BRUSH_TOOL_SIGNAL: lambda _message: self.action_toggle_brush(True),
            SignalCode.ENABLE_ERASER_TOOL_SIGNAL: lambda _message: self.action_toggle_eraser(True),
            SignalCode.ENABLE_MOVE_TOOL_SIGNAL: lambda _message: self.action_toggle_active_grid_area(True),
            SignalCode.ENABLE_SELECTION_TOOL_SIGNAL: lambda _message: self.action_toggle_select(True),
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL: self.on_toggle_tool_signal,
            SignalCode.TOGGLE_TOOL: self.on_toggle_tool_signal,
            SignalCode.TOGGLE_GRID: self.on_toggle_grid_signal,
            SignalCode.CANVAS_UPDATE_CURSOR: self.on_canvas_update_cursor_signal,
        }
        self.splitters = [
            "canvas_splitter"
        ]
        super().__init__(*args, **kwargs)
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

        self.ui.actionToggle_Grid.blockSignals(True)
        self.ui.actionToggle_Grid.setChecked(show_grid)
        self.ui.actionToggle_Grid.blockSignals(False)

        set_widget_state(self.ui.actionToggle_Active_Grid_Area, current_tool is CanvasToolName.ACTIVE_GRID_AREA)
        set_widget_state(self.ui.actionToggle_Brush, current_tool is CanvasToolName.BRUSH)
        set_widget_state(self.ui.actionToggle_Eraser, current_tool is CanvasToolName.ERASER)
        set_widget_state(self.ui.actionToggle_Grid, show_grid is True)
        set_widget_state(self.ui.actionMask_toggle, self.drawing_pad_settings.mask_layer_enabled is True)

    @property
    def current_tool(self):
        return CanvasToolName(self.application_settings.current_tool)

    @property
    def image_pivot_point(self):
        settings = self.application_settings
        try:
            return QPoint(
                settings.pivot_point_x,
                settings.pivot_point_y
            )
        except Exception as e:
            self.logger.error(e)
        return QPoint(0, 0)

    @image_pivot_point.setter
    def image_pivot_point(self, value):
        settings = self.application_settings
        settings.pivot_point_x = value.x()
        settings.pivot_point_y = value.y()
        self.update_application_settings("pivot_point_x", value.x())
        self.update_application_settings("pivot_point_y", value.y())

    @Slot()
    def action_recenter(self):
        self.emit_signal(SignalCode.RECENTER_GRID_SIGNAL)

    @Slot()
    def action_new(self):
        self.emit_signal(SignalCode.CANVAS_CLEAR)

    @Slot()
    def action_import(self):
        self.emit_signal(SignalCode.CANVAS_IMPORT_IMAGE_SIGNAL)

    @Slot()
    def action_export(self):
        self.emit_signal(SignalCode.CANVAS_EXPORT_IMAGE_SIGNAL)

    @Slot()
    def action_undo(self):
        self.emit_signal(SignalCode.UNDO_SIGNAL)

    @Slot()
    def action_redo(self):
        self.emit_signal(SignalCode.REDO_SIGNAL)

    @Slot(bool)
    def action_toggle_grid(self, val: bool):
        self.update_grid_settings("show_grid", val)

    @Slot(bool)
    def action_toggle_brush(self, val: bool):
        self.emit_signal(SignalCode.TOGGLE_TOOL, {
            "tool": CanvasToolName.BRUSH,
            "active": val
        })

    @Slot(bool)
    def action_toggle_eraser(self, val: bool):
        self.emit_signal(SignalCode.TOGGLE_TOOL, {
            "tool": CanvasToolName.ERASER,
            "active": val
        })

    @Slot(bool)
    def action_toggle_mask(self, val: bool):
        self.drawing_pad_settings.mask_layer_enabled = val

    @Slot(bool)
    def action_toggle_active_grid_area(self, val: bool):
        self.emit_signal(SignalCode.TOGGLE_TOOL, {
            "tool": CanvasToolName.ACTIVE_GRID_AREA,
            "active": val
        })

    @Slot(bool)
    def action_toggle_select(self, val: bool):
        self.emit_signal(SignalCode.TOGGLE_TOOL, {
            "tool": CanvasToolName.SELECTION,
            "active": val
        })

    def on_toggle_tool_signal(self, message: dict):
        tool = message.get("tool", None)
        active = message.get("active", False)
        self._update_action_buttons(tool, active)
        self.emit_signal(SignalCode.CANVAS_UPDATE_CURSOR)
    
    def on_toggle_grid_signal(self, message: dict):
        self.ui.actionToggle_Grid.setChecked(message.get("show_grid", True))
    
    def _update_action_buttons(self, tool, active):
        self.ui.actionToggle_Active_Grid_Area.setChecked(tool is CanvasToolName.ACTIVE_GRID_AREA and active)
        self.ui.actionToggle_Brush.setChecked(tool is CanvasToolName.BRUSH and active)
        self.ui.actionToggle_Eraser.setChecked(tool is CanvasToolName.ERASER and active)
        self.ui.actionToggle_Grid.setChecked(self.grid_settings.show_grid)
    
    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, lambda: self.do_draw(force_draw=True))
        self.emit_signal(SignalCode.CANVAS_UPDATE_CURSOR)

    def on_canvas_update_cursor_signal(self, message: dict):
        event = message.get("event", None)
        cursor = None
        if message.get("apply_cursor", None):
            if self.current_tool in (
                CanvasToolName.BRUSH,
                CanvasToolName.ERASER
            ):
                cursor = circle_cursor(
                    Qt.GlobalColor.white,
                    Qt.GlobalColor.transparent,
                    self.brush_settings.size,
                )
            elif self.current_tool is CanvasToolName.ACTIVE_GRID_AREA:
                if event and event.buttons() == Qt.MouseButton.LeftButton:
                    cursor = Qt.CursorShape.ClosedHandCursor
                else:
                    cursor = Qt.CursorShape.OpenHandCursor
        else:
            cursor = Qt.CursorShape.ArrowCursor
        
        if cursor:
            self.setCursor(cursor)

    def toggle_grid(self, _val):
        self.do_draw()

    def do_draw(
        self,
        force_draw: bool = False
    ):
        self.emit_signal(SignalCode.SCENE_DO_DRAW_SIGNAL, {
            "force_draw": force_draw
        })
        self.ui.canvas_container_size = self.ui.canvas_container.viewport().size()
