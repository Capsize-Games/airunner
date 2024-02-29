from functools import partial

from PIL.ImageQt import ImageQt, QPixmap
from PyQt6.QtCore import QPointF, QPoint, Qt, QRect
from PyQt6.QtGui import QMouseEvent, QColor, QBrush
from PyQt6.QtWidgets import QGraphicsView, QGraphicsItemGroup, QGraphicsItem

from airunner.aihandler.logger import Logger
from airunner.enums import CanvasToolName, SignalCode, ServiceCode, CanvasType
from airunner.mediator_mixin import MediatorMixin
from airunner.service_locator import ServiceLocator
from airunner.utils import snap_to_grid, apply_opacity_to_image
from airunner.widgets.canvas.custom_scene import CustomScene, BrushScene
from airunner.widgets.canvas.draggables.active_grid_area import ActiveGridArea
from airunner.widgets.canvas.draggables.draggable_pixmap import DraggablePixmap
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
        self.active_grid_area = None
        self.do_draw_layers = True
        self.initialized = False
        self.drawing = False
        self.pixmaps = {}
        self.register(
            SignalCode.APPLICATION_TOOL_CHANGED_SIGNAL,
            self.on_tool_changed_signal
        )
        self.line_group = QGraphicsItemGroup()
        self.resizeEvent = self.window_resized

        # register signal handlers
        signal_handlers = {
            SignalCode.CANVAS_DO_RESIZE_SIGNAL: self.do_resize_canvas,
            SignalCode.CANVAS_ZOOM_LEVEL_CHANGED: self.on_zoom_level_changed_signal,
            SignalCode.SET_CANVAS_COLOR_SIGNAL: self.set_canvas_color,
            SignalCode.CANVAS_DO_DRAW_SELECTION_AREA_SIGNAL: self.draw_selected_area,
            SignalCode.UPDATE_SCENE_SIGNAL: self.update_scene,
            SignalCode.CANVAS_CLEAR: self.on_canvas_clear_signal,
            SignalCode.CANVAS_CLEAR_LINES_SIGNAL: self.clear_lines,
            SignalCode.SCENE_DO_DRAW_SIGNAL: self.on_canvas_do_draw_signal,
            SignalCode.APPLICATION_MAIN_WINDOW_LOADED_SIGNAL: self.on_main_window_loaded_signal,
            SignalCode.REMOVE_SCENE_ITEM_SIGNAL: self.remove_scene_item,
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

    def on_main_window_loaded_signal(self):
        self.initialized = True

    def on_canvas_do_draw_signal(self, data: dict):
        self.do_draw(
            force_draw=data.get("force_draw", False),
            do_draw_layers=data.get("do_draw_layers", None)
        )

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
        self.draw_layers()
        self.draw_grid()
        self.update_scene()
        self.drawing = False

    def draw_grid(self):
        self.scene.addItem(self.line_group)

    def on_canvas_clear_signal(self):
        self.create_scene()
        self.line_group = QGraphicsItemGroup()
        self.active_grid_area = None
        self.pixmaps = {}
        settings = self.settings
        settings["layers"] = []
        self.settings = settings
        self.emit(SignalCode.LAYER_ADD_SIGNAL)
        self.emit(SignalCode.CANVAS_DO_RESIZE_SIGNAL, {
            "force_draw": True
        })

    def draw_layers(self):
        if not self.do_draw_layers or self.canvas_type == CanvasType.BRUSH.value:
            return
        self.do_draw_layers = False
        layers = self.settings["layers"]
        for index, layer in enumerate(layers):
            image = ServiceLocator.get(ServiceCode.GET_IMAGE_FROM_LAYER)(layer)
            if image is None:
                continue

            image = apply_opacity_to_image(
                image,
                layer["opacity"] / 100.0
            )

            if not layer["visible"]:
                if (
                    index in self.pixmaps and
                    isinstance(self.pixmaps[index], QGraphicsItem) and
                    self.pixmaps[index].scene() == self.scene
                ):
                    self.remove_scene_item(self.pixmaps[index])
            else:
                # If there's an existing pixmap in the layer, remove it from the scene
                if index in self.pixmaps and isinstance(self.pixmaps[index], QGraphicsItem):
                    if self.pixmaps[index].scene() == self.scene:
                        self.remove_scene_item(self.pixmaps[index])
                    del self.pixmaps[index]
                pixmap = QPixmap()
                pixmap.convertFromImage(ImageQt(image))
                self.pixmaps[index] = DraggablePixmap(pixmap)
                self.emit(SignalCode.LAYER_UPDATE_SIGNAL, {
                    "layer": layer,
                    "index": index
                })
                if self.pixmaps[index].scene() != self.scene:
                    self.scene.addItem(self.pixmaps[index])
            continue

    def clear_lines(self):
        self.remove_scene_item(self.line_group)
        self.line_group = QGraphicsItemGroup()

    def register_line_data(self, lines_data):
        for line_data in lines_data:
            try:
                line = self.scene.addLine(*line_data)
                self.line_group.addToGroup(line)
            except TypeError as e:
                self.logger.error(f"TypeError: {e}")

    def set_scene_rect(self):
        canvas_container_size = self.viewport().size()
        self.scene.setSceneRect(
            0,
            0,
            canvas_container_size.width(),
            canvas_container_size.height()
        )

    def update_scene(self):
        self.scene.update()

    def remove_scene_item(self, item):
        if item is None:
            return
        if item.scene() == self.scene:
            self.scene.removeItem(item)

    def draw_selected_area(self):
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

        # Create an ActiveGridArea object if it doesn't exist
        # and add it to the scene
        if not self.active_grid_area:
            self.active_grid_area = ActiveGridArea()
            self.active_grid_area.setZValue(1)
            self.scene.addItem(self.active_grid_area)

    def window_resized(self, event):
        self.do_resize_canvas()

    def do_resize_canvas(
        self,
        data: dict = None,
    ):
        data = {} if not data else data
        kwargs = {
            "settings": data.get("settings", self.settings),
            "force_draw": data.get("force_draw", False),
            "do_draw_layers": data.get("do_draw_layers", None),
            "scene": data.get("scene", self.scene),
            "line_group": data.get("line_group", self.line_group),
            "view_size": data.get("view_size", self.viewport().size())
        }
        self.emit(SignalCode.CANVAS_RESIZE_SIGNAL, kwargs)

    def on_zoom_level_changed_signal(self):
        transform = self.zoom_handler.on_zoom_level_changed()

        # Set the transform
        self.setTransform(transform)

        # Redraw lines
        self.emit(SignalCode.CANVAS_DO_DRAW_SIGNAL)

    def showEvent(self, event):
        super().showEvent(event)
        original_mouse_event = self.mouseMoveEvent
        self.mouseMoveEvent = partial(self.handle_mouse_event, original_mouse_event)
        self.setContentsMargins(0, 0, 0, 0)
        self.create_scene()
        self.emit(
            SignalCode.CANVAS_DO_DRAW_SIGNAL,
            True
        )
        self.toggle_drag_mode()

    def create_scene(self):
        if self.scene and self.scene.painter:
            self.scene.painter.end()
        if self.canvas_type == CanvasType.IMAGE.value:
            self.scene = CustomScene(
                size=self.size()
            )
        else:
            self.scene = BrushScene(
                size=self.size()
            )
        self.setScene(self.scene)
        self.set_canvas_color()

    def set_canvas_color(self):
        if not self.scene:
            return
        color = QColor(self.settings["grid_settings"]["canvas_color"])
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
            self.emit(SignalCode.CANVAS_DO_DRAW_SIGNAL)
        original_mouse_event(event)

    def on_tool_changed_signal(self, _tool: CanvasToolName):
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
            x, y = snap_to_grid(event.pos().x(), event.pos().y(), use_floor)
        else:
            x = event.pos().x()
            y = event.pos().y()

        # Create a new event with the adjusted position
        new_event = QMouseEvent(
            event.type(),
            QPointF(x, y),
            event.button(),
            event.buttons(),
            event.modifiers()
        )
        return new_event

    def mousePressEvent(self, event: QMouseEvent):
        new_event = self.snap_to_grid(event)
        super().mousePressEvent(new_event)

    def mouseMoveEvent(self, event: QMouseEvent):
        new_event = self.snap_to_grid(event, False)
        super().mouseMoveEvent(new_event)
