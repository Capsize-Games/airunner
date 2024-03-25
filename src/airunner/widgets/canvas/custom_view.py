from functools import partial

from PySide6.QtCore import QPointF, QPoint, Qt, QRect, QEvent
from PySide6.QtGui import QMouseEvent, QColor, QBrush
from PySide6.QtWidgets import QGraphicsView, QGraphicsItemGroup

from airunner.aihandler.logger import Logger
from airunner.enums import CanvasToolName, SignalCode, CanvasType, ServiceCode
from airunner.mediator_mixin import MediatorMixin
from airunner.service_locator import ServiceLocator
from airunner.utils import snap_to_grid
from airunner.widgets.canvas.brush_scene import BrushScene
from airunner.widgets.canvas.controlnet_scene import ControlnetScene
from airunner.widgets.canvas.custom_scene import CustomScene
from airunner.widgets.canvas.draggables.active_grid_area import ActiveGridArea
from airunner.widgets.canvas.outpaint_scene import OutpaintScene
from airunner.windows.main.settings_mixin import SettingsMixin
from airunner.widgets.canvas.zoom_handler import ZoomHandler


class CustomGraphicsView(
    QGraphicsView,
    MediatorMixin,
    SettingsMixin
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        MediatorMixin.__init__(self)
        SettingsMixin.__init__(self)
        self.logger = Logger(prefix=self.__class__.__name__)
        self.scene = None
        self.current_background_color = None
        self.active_grid_area = None
        self.do_draw_layers = True
        self.initialized = False
        self.drawing = False
        self.pixmaps = {}
        self.line_group = QGraphicsItemGroup()
        self.scene_is_active = False

        # register signal handlers
        signal_handlers = {
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL: self.on_tool_changed_signal,
            SignalCode.CANVAS_ZOOM_LEVEL_CHANGED: self.on_zoom_level_changed_signal,
            SignalCode.SET_CANVAS_COLOR_SIGNAL: self.set_canvas_color,
            SignalCode.CANVAS_DO_DRAW_SELECTION_AREA_SIGNAL: self.draw_selected_area,
            SignalCode.UPDATE_SCENE_SIGNAL: self.update_scene,
            SignalCode.CANVAS_CLEAR_LINES_SIGNAL: self.clear_lines,
            SignalCode.SCENE_DO_DRAW_SIGNAL: self.on_canvas_do_draw_signal,
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.on_main_window_loaded_signal,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal
        }
        for k, v in signal_handlers.items():
            self.register(k, v)

        ServiceLocator.register(
            ServiceCode.CANVAS_REGISTER_LINE_DATA,
            self.register_line_data
        )

        self.line_group = None
        self.last_pos = QPoint(0, 0)
        self.zoom_handler = ZoomHandler()

    @property
    def canvas_type(self) -> str:
        return self.property("canvas_type")

    def on_main_window_loaded_signal(self, _message):
        self.initialized = True

    def on_canvas_do_draw_signal(self, data: dict):
        self.do_draw(
            force_draw=data.get("force_draw", False),
            do_draw_layers=data.get("do_draw_layers", None)
        )

    def on_application_settings_changed_signal(self, _message):
        self.set_canvas_color()

    def do_draw(
        self,
        force_draw: bool = False,
        do_draw_layers: bool = None
    ):
        if do_draw_layers is not None:
            self.do_draw_layers = do_draw_layers
        if (self.drawing or not self.initialized) and not force_draw:
            return
        self.drawing = True
        self.set_scene_rect()
        self.draw_grid()
        self.show_active_grid_area()
        self.update_scene()
        self.drawing = False

    def draw_grid(self):
        if self.canvas_type != CanvasType.IMAGE.value:
            return
        if self.line_group is not None:
            self.scene.addItem(self.line_group)

    def clear_lines(self, _message):
        self.remove_scene_item(self.line_group)
        self.line_group = QGraphicsItemGroup()

    def register_line_data(self, lines_data):
        for line_data in lines_data:
            try:
                line = self.scene.addLine(*line_data)
                self.line_group.addToGroup(line)
            except TypeError as e:
                self.logger.error(f"TypeError: {e}")
            except AttributeError as e:
                self.logger.error(f"AttributeError: {e}")

    def set_scene_rect(self):
        canvas_container_size = self.viewport().size()
        self.scene.setSceneRect(
            0,
            0,
            canvas_container_size.width(),
            canvas_container_size.height()
        )

    def update_scene(self, _message=None):
        self.scene.update()

    def remove_scene_item(self, item):
        if item is None:
            return
        if item.scene() == self.scene:
            self.scene.removeItem(item)

    def draw_selected_area(self, _message):
        """
        Draw the selected active grid area container
        """
        # Handle any active selections
        selection_start_pos = self.scene.selection_start_pos
        selection_stop_pos = self.scene.selection_stop_pos

        # This will clear the active grid area while a selection is being made
        if selection_stop_pos is None and selection_start_pos is not None:
            if self.active_grid_area:
                self.remove_scene_item(self.active_grid_area)
                self.active_grid_area = None
            return

        # this will update the active grid area in the settings
        if selection_start_pos is not None and selection_stop_pos is not None:
            rect = QRect(
                selection_start_pos,
                selection_stop_pos
            )

            # Ensure width and height ar divisible by 8
            width = rect.width()
            height = rect.height()
            if width % 8 != 0:
                width -= width % 8
            if height % 8 != 0:
                height -= height % 8

            cell_size = self.settings["grid_settings"]["cell_size"]
            if width < cell_size:
                width = cell_size
            if height < cell_size:
                height = cell_size

            x = rect.x()
            y = rect.y()

            # update the active grid area in settings
            settings = self.settings
            active_grid_settings = settings["active_grid_settings"]
            active_grid_settings["pos_x"] = x
            active_grid_settings["pos_y"] = y
            active_grid_settings["width"] = width
            active_grid_settings["height"] = height
            generator_settings = settings["generator_settings"]
            generator_settings["width"] = width
            generator_settings["height"] = height
            settings["active_grid_settings"] = active_grid_settings
            settings["generator_settings"] = generator_settings
            settings["working_width"] = width
            settings["working_height"] = height
            self.settings = settings

            # Clear the selection from the scene
            self.scene.clear_selection()
        self.show_active_grid_area()
        self.emit_signal(
            SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED,
            {
                "settings": self.settings
            }
        )

    def show_active_grid_area(self):
        if self.canvas_type != CanvasType.IMAGE.value:
            return

        # Create an ActiveGridArea object if it doesn't exist
        # and add it to the scene
        if not self.active_grid_area:
            self.active_grid_area = ActiveGridArea()
            self.active_grid_area.setZValue(1)
            self.scene.addItem(self.active_grid_area)

    def on_zoom_level_changed_signal(self, _message):
        transform = self.zoom_handler.on_zoom_level_changed()

        # Set the transform
        self.setTransform(transform)

        # Redraw lines
        self.emit_signal(SignalCode.CANVAS_DO_DRAW_SIGNAL)

    def showEvent(self, event):
        super().showEvent(event)

        if self.canvas_type == CanvasType.IMAGE.value:
            original_mouse_event = self.mouseMoveEvent
            self.mouseMoveEvent = partial(
                self.handle_mouse_event,
                original_mouse_event
            )

        self.setContentsMargins(0, 0, 0, 0)
        self.create_scene()

        if self.canvas_type == CanvasType.IMAGE.value:
            self.emit_signal(
                SignalCode.CANVAS_DO_DRAW_SIGNAL,
                True
            )

        self.toggle_drag_mode()

    def create_scene(self):
        if self.scene and self.scene.painter:
            self.scene.painter.end()
        if self.canvas_type == CanvasType.IMAGE.value:
            self.scene = CustomScene(
                self.canvas_type
            )
        elif self.canvas_type == CanvasType.BRUSH.value:
            self.scene = BrushScene(
                self.canvas_type
            )
        elif self.canvas_type == CanvasType.CONTROLNET.value:
            self.scene = ControlnetScene(
                self.canvas_type
            )
        elif self.canvas_type == CanvasType.OUTPAINT.value:
            self.scene = OutpaintScene(
                self.canvas_type
            )
        self.setScene(self.scene)
        self.set_canvas_color()

    def set_canvas_color(self, _message=None):
        if not self.scene:
            return
        if self.current_background_color == self.settings["grid_settings"]["canvas_color"]:
            return
        self.current_background_color = self.settings["grid_settings"]["canvas_color"]
        color = QColor(self.current_background_color)
        brush = QBrush(color)
        self.scene.setBackgroundBrush(brush)

    def handle_mouse_event(self, original_mouse_event, event):
        if event.buttons() == Qt.MouseButton.MiddleButton:
            if self.last_pos:
                delta = event.pos() - self.last_pos
                horizontal_value = self.horizontalScrollBar().value()
                vertical_value = self.verticalScrollBar().value()
                horizontal_value -= delta.x()
                vertical_value -= delta.y()
                self.horizontalScrollBar().setValue(horizontal_value)
                self.verticalScrollBar().setValue(vertical_value)
            self.last_pos = event.pos()
            self.emit_signal(SignalCode.CANVAS_DO_DRAW_SIGNAL)
        original_mouse_event(event)

    def on_tool_changed_signal(self, message):
        _tool: CanvasToolName = message["tool"]
        self.toggle_drag_mode()

    def toggle_drag_mode(self):
        current_tool = self.settings["current_tool"]
        if current_tool is CanvasToolName.SELECTION:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def snap_to_grid(self, event: QMouseEvent, use_floor: bool = True) -> QMouseEvent:
        """
        This is used to adjust the selection tool to the grid
        in real time during rubberband mode.
        :param event:
        :return:
        """
        if self.settings["current_tool"] == CanvasToolName.SELECTION:
            x, y = snap_to_grid(self.settings, event.pos().x(), event.pos().y(), use_floor)
        else:
            x = event.pos().x()
            y = event.pos().y()

        x = float(x)
        y = float(y)

        point = QPointF(x, y)
        event_type: QEvent.Type = QEvent.Type(event.type())

        new_event = QMouseEvent(
            event_type,
            point,
            event.button(),
            event.buttons(),
            event.modifiers()
        )
        return new_event

    def mousePressEvent(self, event: QMouseEvent):
        settings = self.settings
        settings["canvas_settings"]["active_canvas"] = self.canvas_type
        self.settings = settings
        new_event = self.snap_to_grid(event)
        super().mousePressEvent(new_event)
