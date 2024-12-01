from functools import partial

from PySide6 import QtGui
from PySide6.QtCore import QPointF, QPoint, Qt, QRect, QEvent
from PySide6.QtGui import QMouseEvent, QColor, QBrush, QPen
from PySide6.QtWidgets import QGraphicsView, QGraphicsItemGroup, QGraphicsLineItem

from airunner.enums import CanvasToolName, SignalCode, CanvasType
from airunner.mediator_mixin import MediatorMixin
from airunner.utils.image.convert_image_to_binary import convert_image_to_binary
from airunner.utils.snap_to_grid import snap_to_grid
from airunner.widgets.canvas.brush_scene import BrushScene
from airunner.widgets.canvas.custom_scene import CustomScene
from airunner.widgets.canvas.draggables.active_grid_area import ActiveGridArea
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
        
        self._scene = None
        self.current_background_color = None
        self.active_grid_area = None
        self.do_draw_layers = True
        self.initialized = False
        self.drawing = False
        self.pixmaps = {}
        self.line_group = QGraphicsItemGroup()
        self._scene_is_active = False

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
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.ACTIVE_GRID_AREA_MOVED_SIGNAL: self.handle_active_grid_area_moved_signal,
            SignalCode.MASK_GENERATOR_WORKER_RESPONSE_SIGNAL: self.on_mask_generator_worker_response_signal,
        }

        for k, v in signal_handlers.items():
            self.register(k, v)

        self.line_group = None
        self.last_pos = QPoint(0, 0)
        self.zoom_handler = ZoomHandler()

    @property
    def current_tool(self):
        return CanvasToolName(self.application_settings.current_tool)

    @property
    def canvas_type(self) -> str:
        return self.property("canvas_type")

    @property
    def __do_show_active_grid_area(self):
        return self.canvas_type in (
            CanvasType.IMAGE.value,
            CanvasType.BRUSH.value,
        )

    @property
    def __can_draw_grid(self):
        return self.grid_settings.show_grid and self.canvas_type in (
            CanvasType.IMAGE.value,
            CanvasType.BRUSH.value,
        )

    def handle_active_grid_area_moved_signal(self):
        self.active_grid_area.snap_to_grid()

    def on_mask_generator_worker_response_signal(self, message: dict):
        mask = message["mask"]
        if mask is not None:
            mask = convert_image_to_binary(mask)
            self.update_drawing_pad_settings("mask", mask)

    def on_main_window_loaded_signal(self):
        self.initialized = True
        self.do_draw()

    def on_canvas_do_draw_signal(self, data: dict):
        self.do_draw(force_draw=data.get("force_draw", False))

    def on_application_settings_changed_signal(self):
        self.set_canvas_color()
        if self.grid_settings.show_grid:
            self.do_draw()
        else:
            self.clear_lines()

    def do_draw(
        self,
        force_draw: bool = False
    ):
        if (self.drawing or not self.initialized) and not force_draw:
            return
        self.drawing = True
        self.set_scene_rect()
        if self.grid_settings.show_grid:
            self.draw_grid()
        else:
            self.clear_lines()
        self.show_active_grid_area()
        self.update_scene()
        self.drawing = False

    def draw_grid(self):
        if not self.__can_draw_grid:
            pass

        if self.line_group is None:
            self.line_group = QGraphicsItemGroup()

        if self.line_group.scene() != self._scene:
            self._scene.addItem(self.line_group)

        cell_size = self.grid_settings.cell_size
        scene_width = int(self._scene.width())
        scene_height = int(self._scene.height())

        num_vertical_lines = scene_width // cell_size + 1
        num_horizontal_lines = scene_height // cell_size + 1

        color = QColor(self.grid_settings.line_color)
        pen = QPen(
            color,
            self.grid_settings.line_width,
        )

        # Create or reuse vertical lines
        for i in range(num_vertical_lines):
            x = i * cell_size
            if i < len(self.line_group.childItems()):
                line = self.line_group.childItems()[i]
                line.setLine(x, 0, x, scene_height)
                line.setVisible(True)
                line.setPen(pen)
            else:
                line = QGraphicsLineItem(x, 0, x, scene_height)
                self.line_group.addToGroup(line)

        # Create or reuse horizontal lines
        for i in range(num_horizontal_lines):
            y = i * cell_size
            index = i + num_vertical_lines
            if index < len(self.line_group.childItems()):
                line = self.line_group.childItems()[index]
                line.setLine(0, y, scene_width, y)
                line.setVisible(True)
                line.setPen(pen)
            else:
                line = QGraphicsLineItem(0, y, scene_width, y)
                self.line_group.addToGroup(line)

        # Hide unused lines
        for i in range(num_vertical_lines + num_horizontal_lines, len(self.line_group.childItems())):
            self.line_group.childItems()[i].setVisible(False)

    def clear_lines(self):
        self.remove_scene_item(self.line_group)

    def register_line_data(self, lines_data):
        for line_data in lines_data:
            try:
                line = self._scene.addLine(*line_data)
                self.line_group.addToGroup(line)
            except TypeError as e:
                self.logger.error(f"TypeError: {e}")
            except AttributeError as e:
                self.logger.error(f"AttributeError: {e}")

    def set_scene_rect(self):
        if not self._scene:
            return
        canvas_container_size = self.viewport().size()
        self._scene.setSceneRect(
            0,
            0,
            canvas_container_size.width(),
            canvas_container_size.height()
        )

    def update_scene(self):
        if not self._scene:
            return
        self._scene.update()

    def remove_scene_item(self, item):
        if item is None:
            return
        if item.scene() == self._scene:
            self._scene.removeItem(item)

    def draw_selected_area(self):
        """
        Draw the selected active grid area container
        """
        # Handle any active selections
        selection_start_pos = self._scene.selection_start_pos
        selection_stop_pos = self._scene.selection_stop_pos

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

            cell_size = self.grid_settings.cell_size
            if width < cell_size:
                width = cell_size
            if height < cell_size:
                height = cell_size

            x = rect.x()
            y = rect.y()

            self.update_active_grid_settings("pos_x", x)
            self.update_active_grid_settings("pos_y", y)
            self.update_generator_settings("width", width)
            self.update_generator_settings("height", height)
            self.update_application_settings("working_width", width)
            self.update_application_settings("working_height", height)

            # Clear the selection from the scene
            self._scene.clear_selection()
        self.show_active_grid_area()
        self.emit_signal(SignalCode.APPLICATION_ACTIVE_GRID_AREA_UPDATED)

    def show_active_grid_area(self):
        if not self.__do_show_active_grid_area:
            return

        # Create an ActiveGridArea object if it doesn't exist
        # and add it to the scene
        if not self.active_grid_area:
            self.active_grid_area = ActiveGridArea()
            self.active_grid_area.setZValue(10)
            self._scene.addItem(self.active_grid_area)

    def on_zoom_level_changed_signal(self):
        transform = self.zoom_handler.on_zoom_level_changed()

        # Set the transform
        self.setTransform(transform)

        # Redraw lines
        self.do_draw()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setSceneRect(0, 0, self.viewport().width(), self.viewport().height())
        self.do_draw()

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

        self.do_draw(True)

        self._scene.initialize_image()

        self.toggle_drag_mode()

        # Ensure the viewport is aligned to the top-left corner
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setSceneRect(0, 0, self.viewport().width(), self.viewport().height())


    def create_scene(self):
        if self._scene and self._scene.painter:
            self._scene.painter.end()
        if self.canvas_type == CanvasType.IMAGE.value:
            self._scene = CustomScene(self.canvas_type)
        elif self.canvas_type == CanvasType.BRUSH.value:
            self._scene = BrushScene(self.canvas_type)
        self.setScene(self._scene)
        self.set_canvas_color()

    def set_canvas_color(self):
        if not self._scene:
            return
        if self.current_background_color == self.grid_settings.canvas_color:
            return
        self.current_background_color = self.grid_settings.canvas_color
        color = QColor(self.current_background_color)
        brush = QBrush(color)
        self._scene.setBackgroundBrush(brush)

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
            self.do_draw()
        original_mouse_event(event)

    def on_tool_changed_signal(self, message):
        _tool: CanvasToolName = message["tool"]
        self.toggle_drag_mode()

    def toggle_drag_mode(self):
        if self.current_tool is CanvasToolName.SELECTION:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def snap_to_grid(self, event: QMouseEvent, use_floor: bool = True) -> QMouseEvent:
        """
        This is used to adjust the selection tool to the grid
        in real time during rubberband mode.
        :param event:
        :param use_floor:
        :return:
        """
        if self.current_tool is CanvasToolName.SELECTION:
            x, y = snap_to_grid(self.grid_settings, event.pos().x(), event.pos().y(), use_floor)
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
        new_event = self.snap_to_grid(event)
        super().mousePressEvent(new_event)
