from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QColor, QPainter, QBrush, QCursor
from airunner.cursors.circle_brush import CircleCursor
from airunner.mixins.canvas_active_grid_area_mixin import CanvasActiveGridAreaMixin
from airunner.mixins.canvas_brushes_mixin import CanvasBrushesMixin
from airunner.mixins.canvas_grid_mixin import CanvasGridMixin
from airunner.mixins.canvas_image_mixin import CanvasImageMixin
from airunner.mixins.canvas_layer_mixin import CanvasLayerMixin
from airunner.mixins.canvas_selectionbox_mixin import CanvasSelectionboxMixin
from airunner.mixins.canvas_widgets_mixin import CanvasWidgetsMixin
from airunner.models.linedata import LineData


class Canvas(
    CanvasBrushesMixin,
    CanvasGridMixin,
    CanvasWidgetsMixin,
    CanvasImageMixin,
    CanvasSelectionboxMixin,
    CanvasActiveGridAreaMixin,
    CanvasLayerMixin,
):
    saving = False
    select_start = None
    select_end = None
    shift_is_pressed = False
    left_mouse_button_down = False
    brush_start = None
    last_mouse_pos = None

    @property
    def image_pivot_point(self):
        return self.current_layer.image_data.image_pivot_point

    @image_pivot_point.setter
    def image_pivot_point(self, value):
        self.current_layer.image_data.image_pivot_point = value

    @property
    def image_root_point(self):
        return self.current_layer.image_data.image_root_point

    @image_root_point.setter
    def image_root_point(self, value):
        self.current_layer.image_data.image_root_point = value

    @property
    def current_layer(self):
        if len(self.layers) == 0:
            return None
        return self.layers[self.current_layer_index]

    @property
    def select_selected(self):
        return self.settings_manager.settings.current_tool.get() == "select"

    @property
    def eraser_selected(self):
        return self.settings_manager.settings.current_tool.get() == "eraser"

    @property
    def brush_selected(self):
        return self.settings_manager.settings.current_tool.get() == "brush"

    @property
    def move_selected(self):
        return self.settings_manager.settings.current_tool.get() == "move"

    @property
    def is_dragging(self):
        return False

    @property
    def is_zooming(self):
        return False

    @property
    def mouse_pos(self):
        return self.canvas_container.mapFromGlobal(QCursor.pos())

    @property
    def brush_size(self):
        return self.settings_manager.settings.mask_brush_size.get()

    @property
    def canvas_container(self):
        return self.parent.window.canvas_container

    @property
    def settings_manager(self):
        return self.parent.settings_manager

    @property
    def mouse_position(self):
        return self.canvas_container.mapFromGlobal(QCursor.pos())

    @property
    def is_drawing(self):
        return self.left_mouse_button_down and self.brush_selected

    @property
    def primary_color(self):
        return QColor(self.settings_manager.settings.primary_color.get())

    @property
    def viewport_rect(self):
        rect = self.canvas_container.contentsRect()
        rect = QRect(0, 0, rect.width(), rect.height())
        return rect

    def get_layer_opacity(self, index):
        return self.layers[index].opacity

    def set_layer_opacity(self, index, opacity):
        layer = self.layers[index]
        layer.opacity = opacity
        self.update()
        layer.image_data.image = self.apply_opacity(layer.image_data.image, opacity)

    def __init__(
        self,
        parent=None
    ):
        self.canvas_rect = QRect(0, 0, 0, 0)
        self.pos_x = 0
        self.pos_y = 0
        self.current_layer_index = 0
        self.is_erasing = False
        self.parent = parent

        CanvasGridMixin.initialize(self)
        CanvasActiveGridAreaMixin.initialize(self)
        CanvasLayerMixin.initialize(self)
        CanvasBrushesMixin.initialize(self)
        CanvasImageMixin.initialize(self)

        # Set initial position and size of the canvas
        self.canvas_container.setGeometry(QRect(
            int(self.canvas_rect.x()),
            int(self.canvas_rect.y()),
            int(self.canvas_rect.width()),
            int(self.canvas_rect.height())
        ))

        # set self.parent paintEvent
        self.canvas_container.paintEvent = self.paintEvent
        self.canvas_container.mousePressEvent = self.mouse_press_event
        self.canvas_container.mouseMoveEvent = self.mouse_move_event
        self.canvas_container.mouseReleaseEvent = self.mouse_release_event

        # on shift down
        self.parent.window.keyPressEvent = self.key_press_event

        # on key up
        self.parent.window.keyReleaseEvent = self.key_release_event

        # on mouse hover
        self.canvas_container.enterEvent = self.enter_event
        self.canvas_container.leaveEvent = self.leave_event

        # Set the default brush color for drawing
        self.brush = QBrush()
        self.brush.setStyle(Qt.BrushStyle.SolidPattern)

        # Set the initial position for mouse dragging
        self.drag_pos = QPoint(0, 0)

        self.set_canvas_color()

    def timerEvent(self, event):
        pass

    def key_press_event(self, event):
        if event.key() == Qt.Key.Key_Shift:
            self.shift_is_pressed = True

    def key_release_event(self, event):
        if event.key() == Qt.Key.Key_Shift:
            self.shift_is_pressed = False

    def set_canvas_color(self):
        self.canvas_container.setStyleSheet(f"background-color: {self.settings_manager.settings.canvas_color.get()};")
        self.canvas_container.setAutoFillBackground(True)

    def paintEvent(self, event):
        CanvasGridMixin.paintEvent(self, event)
        layers = self.layers.copy()
        layers.reverse()
        for index in range(len(layers)):
            layer = layers[index]
            if not layer.visible:
                continue
            if self.settings_manager.settings.show_active_image_area.get():
                self.draw_active_image_area()
            CanvasImageMixin.draw(self, layer, index)
            CanvasBrushesMixin.draw(self, layer, index)
            CanvasWidgetsMixin.draw(self, layer, index)
        CanvasSelectionboxMixin.paint_event(self, event)
        CanvasActiveGridAreaMixin.paint_event(self, event)

    def draw_active_image_area(self):
        """
        Draw a border around the active image area and fill the background with white
        :return:
        """
        # first iterate over all layers and get extremities
        left = None
        top = None
        right = None
        bottom = None
        for layer in self.layers:
            image_data = layer.image_data
            if image_data.image is None:
                continue
            left = min(left, image_data.position.x()) if left is not None else image_data.position.x()
            top = min(top, image_data.position.y()) if top is not None else image_data.position.y()
            right = max(right, image_data.image.width) if right is not None else image_data.image.width
            bottom = max(bottom, image_data.image.height) if bottom is not None else image_data.image.height
        if left is None or top is None or right is None or bottom is None:
            return

        painter = QPainter(self.canvas_container)
        color = QColor(255, 255, 255, 128)
        painter.setPen(color)
        painter.setBrush(color)
        painter.drawRect(self.pos_x + left, self.pos_y + top, right, bottom)
        painter.end()

    def enter_event(self, event):
        self.update_cursor()

    def update_cursor(self):
        if self.brush_selected or self.eraser_selected:
            self.canvas_container.setCursor(CircleCursor(Qt.GlobalColor.white, Qt.GlobalColor.transparent, self.brush_size))
        elif self.move_selected:
            self.canvas_container.setCursor(Qt.CursorShape.OpenHandCursor)
        elif self.active_grid_area_selected:
            self.canvas_container.setCursor(Qt.CursorShape.DragMoveCursor)
        else:
            self.canvas_container.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def leave_event(self, event):
        self.canvas_container.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def update(self):
        self.parent.window.canvas_position.setText(f"X: {-self.pos_x}, Y: {self.pos_y}")

        self.canvas_container.update(self.viewport_rect)

    def clear(self):
        self.current_layer.lines = []
        self.current_layer.image_data = None
        self.update()

    def recenter(self):
        self.pos_x = 0
        self.pos_y = 0
        self.update()

    def handle_move_canvas(self, event):
        self.pos_x += event.pos().x() - self.drag_pos.x()
        self.pos_y += event.pos().y() - self.drag_pos.y()
        self.drag_pos = event.pos()
        self.update()

    def handle_move_layer(self, event):
        point = QPoint(
            event.pos().x() if self.drag_pos is not None else 0,
            event.pos().y() if self.drag_pos is not None else 0
        )
        # snap to grid
        grid_size = self.settings_manager.settings.size.get()
        point.setX(point.x() - (point.x() % grid_size))
        point.setY(point.y() - (point.y() % grid_size))

        # center the image
        # point.setX(int((point.x() - self.current_layer.images[0].image.size[0] / 2)))
        # point.setY(int((point.y() - self.current_layer.images[0].image.size[1] / 2)))

        # establish a rect based on line points - we need the area that is being moved
        # so that we can center the point on it
        rect = QRect()
        for line in self.current_layer.lines:
            rect = rect.united(QRect(line.start_point, line.end_point))

        try:
            rect = rect.united(QRect(
                self.current_layer.image_data.position.x(),
                self.current_layer.image_data.position.y(),
                self.current_layer.image_data.image.size[0],
                self.current_layer.image_data.image.size[1]
            ))
        except IndexError:
            pass

        # center the point on the rect
        point.setX(int(point.x() - int(rect.width() / 2)))
        point.setY(int(point.y() - int(rect.height() / 2)))

        self.layers[self.current_layer_index].offset = point

    def mouse_press_event(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.select_start = event.pos()
            if self.brush_selected:
                self.last_mouse_pos = event.pos()
                start = event.pos() - QPoint(self.pos_x, self.pos_y)
                end = event.pos() - QPoint(self.pos_x, self.pos_y)
                pen = self.pen(event)
                line = LineData(start, end, pen, self.current_layer_index)
                start += self.layers[self.current_layer_index].offset
                end += self.layers[self.current_layer_index].offset
                self.current_layer.lines += [line]

                if event.button() == Qt.MouseButton.LeftButton and not self.left_mouse_button_down:
                    self.left_mouse_button_down = True
                    self.brush_start = start

            self.handle_tool(event)
            self.update()
        elif event.button() == Qt.MouseButton.MiddleButton:
            # Start dragging the canvas when the middle or right mouse button is pressed
            self.drag_pos = event.pos()

    def mouse_move_event(self, event):
        # check if LeftButton is pressed
        if Qt.MouseButton.LeftButton in event.buttons():
            self.last_mouse_pos = event.pos()
            self.handle_tool(event)
            self.update()
        elif Qt.MouseButton.MiddleButton in event.buttons() and self.drag_pos is not None:
            self.handle_move_canvas(event)
    
    def mouse_release_event(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.left_mouse_button_down = False
            if self.eraser_selected:
                self.last_pos = None
                self.is_erasing = False
            elif self.brush_selected:
                self.rasterize_lines(final=True)
        elif event.button() == Qt.MouseButton.MiddleButton:
            # Start dragging the canvas when the middle or right mouse button is pressed
            self.drag_pos = event.pos()

    def handle_select(self, event):
        if self.select_selected:
            if self.select_start is None:
                self.select_start = event.pos()
            else:
                self.select_end = event.pos()

        # snap to grid if enabled
        if self.settings_manager.settings.snap_to_grid.get():
            grid_size = self.settings_manager.settings.size.get()
            self.select_start.setX(self.select_start.x() - (self.select_start.x() % grid_size))
            self.select_start.setY(self.select_start.y() - (self.select_start.y() % grid_size))
            self.select_end.setX(self.select_end.x() - (self.select_end.x() % grid_size))
            self.select_end.setY(self.select_end.y() - (self.select_end.y() % grid_size))

        self.update()

    def handle_tool(self, event):
        if self.eraser_selected:
            if not self.is_erasing:
                self.parent.history.add_event({
                    "event": "erase",
                    "layer_index": self.current_layer_index,
                    "lines": self.current_layer.lines.copy(),
                    "images": self.image_data_copy(self.current_layer_index)
                })
            self.handle_erase(event)
            self.parent.is_dirty = True
        elif self.brush_selected:
            self.handle_draw(event)
            self.parent.is_dirty = True
        elif self.move_selected:
            self.handle_move_layer(event)
            self.parent.is_dirty = True
        elif self.select_selected:
            self.handle_select(event)
        elif self.active_grid_area_selected:
            self.handle_move_active_grid_area(event)

    def handle_move_active_grid_area(self, event):
        pos = event.pos()
        point = QPoint(
            pos.x(),
            pos.y()
        )

        # drag from the center of active_grid_area_pivot_point based on the size
        width = self.settings_manager.settings.working_width.get()
        height = self.settings_manager.settings.working_height.get()
        point -= QPoint(
            int((width / 2) + self.pos_x),
            int((height / 2) + self.pos_y)
        )

        if self.settings_manager.settings.snap_to_grid.get():
            point = QPoint(
                point.x() - (point.x() % self.grid_size),
                point.y() - (point.y() % self.grid_size)
            )

        self.active_grid_area_pivot_point = point

        # trigger draw event
        self.update()

    def reset_settings(self):
        self.parent.window.width_slider.setValue(self.settings_manager.settings.working_width.get())
        self.parent.window.height_slider.setValue(self.settings_manager.settings.working_height.get())

    def update_canvas_color(self, color):
        self.parent.window.canvas_container.setStyleSheet(f"background-color: {color};")
        self.parent.window.canvas_container.setAutoFillBackground(True)
        self.update()
