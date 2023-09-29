from functools import partial

from PIL import Image
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QColor, QPainter, QBrush, QCursor
from PyQt6.QtWidgets import QSpacerItem, QSizePolicy, QVBoxLayout, QWidget

from airunner.aihandler.qtvar import BooleanVar
from airunner.cursors.circle_brush import CircleCursor
from airunner.mixins.canvas_active_grid_area_mixin import CanvasActiveGridAreaMixin
from airunner.mixins.canvas_brushes_mixin import CanvasBrushesMixin
from airunner.mixins.canvas_grid_mixin import CanvasGridMixin
from airunner.mixins.canvas_image_mixin import CanvasImageMixin
from airunner.mixins.canvas_selectionbox_mixin import CanvasSelectionboxMixin
from airunner.mixins.canvas_widgets_mixin import CanvasWidgetsMixin
from airunner.models.layerdata import LayerData
from airunner.models.linedata import LineData
from airunner.widgets.layers.layer_widget import LayerWidget


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
    selected_layers = {}
    container = None

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
        if len(self.layers) == 0:
            return None
        return self.layers[self.current_layer_index]

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
        return self.settings_manager.brush_settings.brush_size

    @property
    def canvas_container(self):
        return self.parent.ui.canvas_widget.ui.canvas_container

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
        return QColor(self.settings_manager.brush_settings.primary_color)

    @property
    def viewport_rect(self):
        rect = self.canvas_container.contentsRect()
        rect = QRect(0, 0, rect.width(), rect.height())
        return rect

    def get_layer_opacity(self, index):
        return self.layers[index].opacity

    def set_layer_opacity(self, opacity: int):
        opacity = opacity / 100
        self.current_layer.opacity = opacity
        self.update()
        self.current_layer.image_data.image = self.apply_opacity(self.current_layer.image_data.image, opacity)

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
        self.layers = []
        self.add_layer()

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

        # set self.parent paintEvent
        self.canvas_container.paintEvent = self.paintEvent
        self.canvas_container.mousePressEvent = self.mouse_press_event
        self.canvas_container.mouseMoveEvent = self.mouse_move_event
        self.canvas_container.mouseReleaseEvent = self.mouse_release_event

        # on shift down
        # self.parent.window.keyPressEvent = self.keyPressEvent

        # on key up
        # self.parent.window.keyReleaseEvent = self.keyReleaseEvent

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
        self.parent.canvas_position = f"X {-self.pos_x: 05d} Y {self.pos_y: 05d}"
        self.canvas_container.update(self.viewport_rect)
        self.parent.update()

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
        grid_size = self.settings_manager.grid_settings.size
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
        self.update()

    _is_canvas_drag_mode = False

    @property
    def is_canvas_drag_mode(self):
        return self._is_canvas_drag_mode

    @is_canvas_drag_mode.setter
    def is_canvas_drag_mode(self, value):
        self._is_canvas_drag_mode = value
        self.update_cursor()

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
        if self.settings_manager.grid_settings.snap_to_grid:
            grid_size = self.settings_manager.grid_settings.size
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
            self.is_dirty = True
        elif self.brush_selected:
            self.handle_draw(event)
            self.is_dirty = True
        elif self.move_selected:
            self.handle_move_layer(event)
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

        if self.settings_manager.grid_settings.snap_to_grid:
            point = QPoint(
                point.x() - (point.x() % self.grid_size),
                point.y() - (point.y() % self.grid_size)
            )

        self.active_grid_area_pivot_point = point

        # trigger draw event
        self.update()

    def reset_settings(self):
        self.parent.header_widget.width_slider_widget.slider.setValue(self.settings_manager.working_width)
        self.parent.header_widget.height_slider_widget.slider.setValue(self.settings_manager.working_height)

    def set_canvas_color(self):
        self.update_canvas_color(self.settings_manager.canvas_color)

    def update_canvas_color(self, color):
        self.canvas_container.setStyleSheet(f"""
            background-color: {color};
        """)
        self.canvas_container.setAutoFillBackground(True)
        self.update()

    # Canvas layer functions
    def track_layer_move_history(self):
        layer_order = []
        for layer in self.layers:
            layer_order.append(layer.uuid)
        self.parent.history.add_event({
            "event": "move_layer",
            "layer_order": layer_order,
            "layer_index": self.current_layer_index
        })

    def move_layer_up(self, layer):
        index = self.layers.index(layer)
        if index == 0:
            return
        # track the current layer order
        self.track_layer_move_history()
        self.layers.remove(layer)
        self.layers.insert(index - 1, layer)
        self.current_layer_index = index - 1
        self.show_layers()
        self.update()

    def move_layer_down(self, layer):
        index = self.layers.index(layer)
        if index == len(self.layers) - 1:
            return
        self.track_layer_move_history()
        self.layers.remove(layer)
        self.layers.insert(index + 1, layer)
        self.current_layer_index = index + 1
        self.show_layers()
        self.update()

    def add_layer(self):
        self.parent.history.add_event({
            "event": "new_layer",
            "layers": self.get_layers_copy(),
            "layer_index": self.current_layer_index
        })
        layer_name = f"Layer {len(self.layers) + 1}"
        self.layers.insert(0, LayerData(len(self.layers), layer_name))
        self.set_current_layer(0)

    def get_layers_copy(self):
        return [layer for layer in self.layers]

    def merge_selected_layers(self):
        if self.current_layer_index not in self.selected_layers:
            self.selected_layers[self.current_layer_index] = self.current_layer

        selected_layer = self.current_layer

        # get the rect of the new image based on the existing images extremities
        # (left, top, width and height)
        rect = QRect()
        for layer in self.selected_layers.values():
            image = layer.image_data.image
            if image:
                if (image.width+layer.image_data.position.x()) > rect.width():
                    rect.setWidth(image.width+abs(layer.image_data.position.x()))
                if (image.height+layer.image_data.position.y()) > rect.height():
                    rect.setHeight(image.height+abs(layer.image_data.position.y()))
                if layer.image_data.position.x() < rect.x():
                    rect.setX(layer.image_data.position.x())
                if layer.image_data.position.y() < rect.y():
                    rect.setY(layer.image_data.position.y())

        new_image = Image.new("RGBA", (rect.width(), rect.height()), (0, 0, 0, 0))

        for index, layer in self.selected_layers.items():
            # get an image object and merge it into the new image if it exists
            image = layer.image_data.image
            if image:
                x = layer.image_data.position.x()
                if x < 0:
                    x = 0
                y = layer.image_data.position.y()
                if y < 0:
                    y = 0
                new_image.alpha_composite(
                    image,
                    (x, y)
                )

            # delete any layers which are not the current layer index
            if index != self.current_layer_index:
                self.delete_layer(layer=layer)

        # if we have a new image object, set it as the current layer image
        layer_index = self.get_index_by_layer(selected_layer)
        self.current_layer_index = layer_index
        if new_image:
            self.layers[self.current_layer_index].image_data.image = new_image
            self.layers[self.current_layer_index].image_data.position = QPoint(rect.x(), rect.y())

        # reset the selected layers dictionary and refresh the canvas
        self.selected_layers = {}
        self.show_layers()
        self.update()

    def get_index_by_layer(self, layer):
        for index, layer_object in enumerate(self.layers):
            if layer is layer_object:
                return index
        return 0

    def delete_layer(self, _value=False, index=None, layer=None):
        current_index = index
        if layer and current_index is None:
            for layer_index, layer_object in enumerate(self.layers):
                if layer_object is layer:
                    current_index = layer_index
        if current_index is None:
            current_index = self.current_layer_index
        self.parent.history.add_event({
            "event": "delete_layer",
            "layers": self.get_layers_copy(),
            "layer_index": current_index
        })
        if len(self.layers) == 1:
            self.layers = [LayerData(0, "Layer 1")]
        else:
            try:
                layer = self.layers.pop(current_index)
                self.container.layout().removeWidget(layer.layer_widget)
                layer.layer_widget.deleteLater()
            except IndexError:
                pass
        self.show_layers()
        self.update()

    def clear_layers(self):
        # delete all widgets from self.container.layout()
        for index, layer in enumerate(self.layers):
            self.container.layout().removeWidget(layer.layer_widget)
            layer.layer_widget.deleteLater()
        self.layers = [LayerData(0, "Layer 1")]
        self.current_layer_index = 0

    def layer_up(self):
        self.move_layer_up(self.current_layer)
        self.show_layers()

    def layer_down(self):
        self.move_layer_down(self.current_layer)
        self.show_layers()

    def new_layer(self):
        self.add_layer()
        self.show_layers()

    def show_layers(self):
        """
        This function is called when the layers need to be updated.
        :return:
        """
        # create an object which can contain a layer_obj and then be added to layers.setWidget
        container = QWidget()
        container.setLayout(QVBoxLayout())

        for layer in self.layers:
            index = self.layers.index(layer)
            layer_obj = LayerWidget(data=layer)
            layer_obj.ui.layer_name.setText(layer.name)

            # onclick of layer_obj set as the current layer index on self
            layer_obj.mousePressEvent = partial(self.handle_layer_click, layer, index)

            # show a border around layer_obj if it is the selected index
            if self.current_layer_index == index:
                layer_obj.ui.frame.setStyleSheet(self.parent.css("layer_highlight_style"))
            else:
                layer_obj.ui.frame.setStyleSheet(self.parent.css("layer_normal_style"))

            layer_obj.set_icon()
            layer_obj.ui.visible_button.clicked.connect(
                lambda _, _layer=layer, _layer_obj=layer_obj: self.toggle_layer_visibility(_layer, _layer_obj))

            container.layout().addWidget(layer_obj)
            layer.layer_widget = layer_obj

        # add a spacer to the bottom of the container
        container.layout().addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # self.parent.tool_menu_widget.layer_container_widget.layers.setWidget(container)
        self.container = container

    def handle_layer_click(self, layer, index, event):
        # check if the control key is pressed
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if self.container:
                if index in self.selected_layers:
                    widget = self.selected_layers[index].layer_widget
                    if widget and index != self.current_layer_index:
                        widget.frame.setStyleSheet(self.parent.css("layer_normal_style"))
                        del self.selected_layers[index]
                else:
                    item = self.container.layout().itemAt(index)
                    if item and index != self.current_layer_index:
                        self.selected_layers[index] = layer
                        self.selected_layers[index].layer_widget.frame.setStyleSheet(
                            self.parent.css("secondary_layer_highlight_style")
                        )
        else:
            for data in self.selected_layers.values():
                data.layer_widget.frame.setStyleSheet(self.parent.css("layer_normal_style"))
            self.set_current_layer(index)
            self.selected_layers = {}

    def toggle_layer_visibility(self, layer, layer_obj):
        # change the eye icon of the visible_button on the layer
        layer.visible = not layer.visible
        self.update()
        layer_obj.set_icon()

    def set_current_layer(self, index):
        if not hasattr(self, "container"):
            return
        if self.container:
            item = self.container.layout().itemAt(self.current_layer_index)
            if item:
                item.widget().frame.setStyleSheet(self.parent.css("layer_normal_style"))
        self.current_layer_index = index
        if self.container:
            item = self.container.layout().itemAt(self.current_layer_index)
            if item:
                item.widget().frame.setStyleSheet(self.parent.css("layer_highlight_style"))
        # change the layer opacity
        # self.parent.tool_menu_widget.set_opacity_slider(
        #     int(self.current_layer.opacity * 100)
        # )

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
                    self.current_active_image_data.position.x() - point.x(),
                    self.current_active_image_data.position.y() - point.y()
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
