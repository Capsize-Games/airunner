from PIL import Image
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QColor, QPainter, QBrush, QCursor

from airunner.aihandler.qtvar import BooleanVar
from airunner.cursors.circle_brush import CircleCursor
from airunner.mixins.canvas_active_grid_area_mixin import CanvasActiveGridAreaMixin
from airunner.mixins.canvas_brushes_mixin import CanvasBrushesMixin
from airunner.mixins.canvas_grid_mixin import CanvasGridMixin
from airunner.mixins.canvas_image_mixin import CanvasImageMixin
from airunner.mixins.canvas_selectionbox_mixin import CanvasSelectionboxMixin
from airunner.mixins.canvas_widgets_mixin import CanvasWidgetsMixin
from airunner.models.linedata import LineData
from airunner.utils import get_main_window


class Canvas(
    CanvasBrushesMixin,
    CanvasGridMixin,
    CanvasWidgetsMixin,
    CanvasImageMixin,
    CanvasSelectionboxMixin,
    CanvasActiveGridAreaMixin,
):
    saving = False
    select_start = None
    select_end = None
    shift_is_pressed = False
    left_mouse_button_down = False
    brush_start = None
    last_mouse_pos = None
    _is_dirty = BooleanVar(False)
    container = None
    _is_canvas_drag_mode = False

    @property
    def is_dirty(self):
        return self._is_dirty.get()

    @is_dirty.setter
    def is_dirty(self, val):
        self._is_dirty.set(val)

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
        return self.app.ui.layer_widget.current_layer

    @property
    def current_layer_index(self):
        return self.app.ui.layer_widget.current_layer_index

    @property
    def layers(self):
        return self.app.ui.layer_widget.layers

    @property
    def select_selected(self):
        return self.settings_manager.current_tool == "select"

    @property
    def eraser_selected(self):
        return self.settings_manager.current_tool == "eraser"

    @property
    def brush_selected(self):
        return self.settings_manager.current_tool == "brush"

    @property
    def move_selected(self):
        return self.settings_manager.current_tool == "move"

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
        return self.settings_manager.brush_settings.size

    @property
    def canvas_container(self):
        return self.app.ui.canvas_widget.ui.canvas_container

    @property
    def settings_manager(self):
        return self.app.settings_manager

    @property
    def mouse_position(self):
        return self.canvas_container.mapFromGlobal(QCursor.pos())

    @property
    def is_drawing(self):
        return self.left_mouse_button_down and self.brush_selected

    @property
    def primary_color(self):
        return QColor(self.settings_manager.brush_settings.primary_color)

    @property
    def viewport_rect(self):
        rect = self.canvas_container.contentsRect()
        rect = QRect(0, 0, rect.width(), rect.height())
        return rect

    @property
    def is_canvas_drag_mode(self):
        return self._is_canvas_drag_mode

    @is_canvas_drag_mode.setter
    def is_canvas_drag_mode(self, value):
        self._is_canvas_drag_mode = value
        self.update_cursor()

    def __init__(self):
        self.canvas_rect = QRect(0, 0, 0, 0)
        self.pos_x = 0
        self.pos_y = 0
        self.is_erasing = False
        self.app = get_main_window()

        CanvasGridMixin.initialize(self)
        CanvasActiveGridAreaMixin.initialize(self)
        CanvasBrushesMixin.initialize(self)
        CanvasImageMixin.initialize(self)

        # Set initial position and size of the canvas
        self.canvas_container.setGeometry(QRect(
            int(self.canvas_rect.x()),
            int(self.canvas_rect.y()),
            int(self.canvas_rect.width()),
            int(self.canvas_rect.height())
        ))

        # set self.app paintEvent
        self.canvas_container.paintEvent = self.paintEvent
        self.canvas_container.mousePressEvent = self.mouse_press_event
        self.canvas_container.mouseMoveEvent = self.mouse_move_event
        self.canvas_container.mouseReleaseEvent = self.mouse_release_event

        # on shift down
        # self.app.window.keyPressEvent = self.keyPressEvent

        # on key up
        # self.app.window.keyReleaseEvent = self.keyReleaseEvent

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

    # def keyPressEvent(self, event):
    #     print("key pressed", event.key())
    #     if event.key() == Qt.Key.Key_Space:
    #         self.is_canvas_drag_mode = True
    #
    #     if event.key() == Qt.Key.Key_Shift:
    #         self.shift_is_pressed = True
    #
    # def keyReleaseEvent(self, event):
    #     print("key released", event.key())
    #     if event.key() == Qt.Key.Key_Space:
    #         print("space up")
    #         self.is_canvas_drag_mode = False
    #
    #     if event.key() == Qt.Key.Key_Shift:
    #         self.shift_is_pressed = False

    def paintEvent(self, event):
        CanvasGridMixin.paintEvent(self, event)
        layers = self.layers.copy()
        layers.reverse()
        for index in range(len(layers)):
            layer = layers[index]
            if not layer.visible:
                continue
            if self.settings_manager.show_active_image_area:
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
            if not len(layer.image_data):
                continue
            image_data = layer.image_data[0]
            left = min(left, image_data.pos_x) if left is not None else image_data.pos_x
            top = min(top, image_data.pos_y) if top is not None else image_data.pos_y
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

    def enter_event(self, _event):
        self.update_cursor()

    def update_cursor(self):
        if self.is_canvas_drag_mode:
            # show as grab cursor
            self.canvas_container.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif self.brush_selected or self.eraser_selected:
            self.canvas_container.setCursor(
                CircleCursor(
                    Qt.GlobalColor.white,
                    Qt.GlobalColor.transparent,
                    self.brush_size
                )
            )
        elif self.move_selected:
            self.canvas_container.setCursor(Qt.CursorShape.OpenHandCursor)
        elif self.active_grid_area_selected:
            self.canvas_container.setCursor(Qt.CursorShape.DragMoveCursor)
        else:
            self.canvas_container.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def leave_event(self, _event):
        self.canvas_container.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def update(self):
        self.canvas_container.update(self.viewport_rect)
        self.app.update()

    def clear(self):
        self.current_layer.lines = []
        self.current_layer.image_data = None
        self.update()

    def handle_move_canvas(self, event):
        self.pos_x += event.pos().x() - self.drag_pos.x()
        self.pos_y += event.pos().y() - self.drag_pos.y()
        self.drag_pos = event.pos()
        self.update()

    def mouse_press_event(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_canvas_drag_mode:
            self.drag_pos = event.pos()
        elif event.button() == Qt.MouseButton.LeftButton:
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
            self.is_canvas_drag_mode = True

    def mouse_move_event(self, event):
        # check if LeftButton is pressed
        if Qt.MouseButton.LeftButton in event.buttons() and self.is_canvas_drag_mode:
            self.handle_move_canvas(event)
        elif Qt.MouseButton.LeftButton in event.buttons():
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
            self.is_canvas_drag_mode = False

    def handle_select(self, event):
        if self.select_selected:
            if self.select_start is None:
                self.select_start = event.pos()
            else:
                self.select_end = event.pos()

        # snap to grid if enabled
        if self.app.snap_to_grid:
            grid_size = self.app.cell_size
            self.select_start.setX(self.select_start.x() - (self.select_start.x() % grid_size))
            self.select_start.setY(self.select_start.y() - (self.select_start.y() % grid_size))
            self.select_end.setX(self.select_end.x() - (self.select_end.x() % grid_size))
            self.select_end.setY(self.select_end.y() - (self.select_end.y() % grid_size))

        self.update()

    def handle_tool(self, event):
        if self.eraser_selected:
            if not self.is_erasing:
                self.app.history.add_event({
                    "event": "erase",
                    "layer_index": self.current_layer_index,
                    "lines": self.current_layer.lines.copy(),
                    "images": self.image_data_copy(self.current_layer_index)
                })
            self.handle_erase(event)
            self.is_dirty = True
        elif self.brush_selected:
            self.handle_draw(event)
            self.is_dirty = True
        elif self.move_selected:
            self.app.ui.layer_widget.handle_move_layer(event)
            self.is_dirty = True
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
        width = self.settings_manager.working_width
        height = self.settings_manager.working_height
        point -= QPoint(
            int((width / 2) + self.pos_x),
            int((height / 2) + self.pos_y)
        )

        if self.app.snap_to_grid:
            point = QPoint(
                point.x() - (point.x() % self.grid_size),
                point.y() - (point.y() % self.grid_size)
            )

        self.active_grid_area_pivot_point = point

        # trigger draw event
        self.update()

    def reset_settings(self):
        self.app.header_widget.width_slider_widget.slider.setValue(self.settings_manager.working_width)
        self.app.header_widget.height_slider_widget.slider.setValue(self.settings_manager.working_height)

    def set_canvas_color(self):
        self.update_canvas_color(self.app.canvas_color)

    def update_canvas_color(self, color):
        self.canvas_container.setStyleSheet(f"""
            background-color: {color};
        """)
        self.canvas_container.setAutoFillBackground(True)
        self.update()

    def delete_outside_active_grid_area(self):
        """
        This function will find the active grid area and delete everything
        on the outside of it for the current layer.
        :return:
        """
        image = self.current_active_image_data.image
        if image:
            # get the sizes and location of the active grid area
            width = self.settings_manager.working_width
            height = self.settings_manager.working_height
            point = self.active_grid_area_pivot_point

            # create a new image and composite the old image into it
            new_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            new_image.alpha_composite(
                image,
                (
                    self.current_active_image_data.pos_x - point.x(),
                    self.current_active_image_data.pos_y - point.y()
                )
            )

            # set the new image and update the grid
            self.current_active_image_data.image = new_image
            self.current_active_image_data.position = QPoint(point.x(), point.y())
            self.current_active_image_data.image_pivot_point = QPoint(point.x(), point.y())
            self.update()

    def delete_inside_active_grid_area(self):
        """
        This function will find the active grid area and delete everything
        on the inside of it for the current layer.
        :return:
        """
        print("delete_inside_active_grid_area")
