import io
import subprocess
from PIL import Image, ImageOps, ImageDraw, ImageGrab
from PIL.ImageQt import ImageQt
from PyQt6.QtCore import Qt, QPoint, QRect, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QPixmap, QCursor, QPainterPath, QPolygonF
from airunner.models.layerdata import LayerData
from airunner.models.imagedata import ImageData
from airunner.models.linedata import LineData

class Canvas:
    saving = False
    select_start = None
    select_end = None

    @property
    def current_active_image(self):
        try:
            return self.current_layer.images[self.current_layer_index]
        except IndexError:
            return None

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
    def active_grid_area_rect(self):
        width = self.settings_manager.settings.working_width.get()
        height = self.settings_manager.settings.working_height.get()

        rect = QRect(
           self.active_grid_area_pivot_point.x(),
           self.active_grid_area_pivot_point.y(),
           self.active_grid_area_pivot_point.x() + width,
           self.active_grid_area_pivot_point.y() + height
        )

        # apply self.pos_x and self.pox_y to the rect
        rect.translate(self.pos_x, self.pos_y)

        return rect

    @property
    def active_grid_area_selected(self):
        return self.settings_manager.settings.current_tool.get() == "active_grid_area"

    @property
    def primary_color(self):
        return QColor(self.settings_manager.settings.primary_color.get())

    @property
    def secondary_color(self):
        return QColor(self.settings_manager.settings.secondary_color.get())

    @property
    def is_dragging(self):
        return False

    @property
    def is_zooming(self):
        return False

    @property
    def grid_size(self):
        return self.settings_manager.settings.size.get()

    @property
    def mouse_pos(self):
        return self.canvas_container.mapFromGlobal(QCursor.pos())

    @property
    def active_grid_area_color(self):
        if self.parent.current_section == "txt2img":
            brush_color = QColor(0, 255, 0)
        elif self.parent.current_section == "img2img":
            brush_color = QColor(255, 0, 0)
        elif self.parent.current_section == "depth2img":
            brush_color = QColor(0, 0, 255)
        elif self.parent.current_section == "pix2pix":
            brush_color = QColor(255, 255, 0)
        elif self.parent.current_section == "outpaint":
            brush_color = QColor(0, 255, 255)
        elif self.parent.current_section == "superresolution":
            brush_color = QColor(255, 0, 255)
        elif self.parent.current_section == "controlnet":
            brush_color = QColor(255, 255, 255)
        else:
            brush_color = QColor(0, 0, 0)
        return brush_color

    def set_current_layer(self, index):
        self.current_layer_index = index

    def apply_filter(self):
        index = 0
        for image in self.current_layer.images:
            self.current_layer.images[index].image = image.image.filter(self.parent.current_filter)
            index += 1

    def get_layers_copy(self):
        return [layer for layer in self.layers]

    def delete_layer(self, index):
        self.parent.history.add_event({
            "event": "delete_layer",
            "layers": self.get_layers_copy(),
            "layer_index": self.current_layer_index
        })

        if len(self.layers) == 1:
            self.layers = [LayerData(0, "Layer 1")]
        else:
            try:
                self.layers.pop(index)
            except IndexError:
                pass
        self.parent.show_layers()
        self.update()

    def toggle_layer_visibility(self, layer):
        layer.visible = not layer.visible
        self.update()

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
        self.parent.show_layers()
        self.update()

    def move_layer_down(self, layer):
        index = self.layers.index(layer)
        if index == len(self.layers) - 1:
            return
        self.track_layer_move_history()
        self.layers.remove(layer)
        self.layers.insert(index + 1, layer)
        self.current_layer_index = index + 1
        self.parent.show_layers()
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

    def __init__(
        self,
        parent=None
    ):
        self.canvas_rect = QRect(0, 0, 0, 0)
        self.pos_x = 0
        self.pos_y = 0
        self.layers = []
        self.current_layer_index = 0
        self.active_grid_area_pivot_point = QPoint(0, 0)
        self.is_erasing = False
        self.start_drawing_line_index = 0
        self.stop_drawing_line_index = 0

        self.parent = parent
        self.settings_manager = parent.settings_manager
        self.add_layer()

        self.image_pivot_point = QPoint(0, 0)
        self.image_root_point = QPoint(0, 0)

        self.canvas_container = parent.window.canvas_container

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
        # on mouse hover
        self.canvas_container.enterEvent = self.enter_event
        self.canvas_container.leaveEvent = self.leave_event

        #self.setParent(parent)

        # Set the default brush color for drawing
        self.brush = QBrush()
        self.brush.setStyle(Qt.BrushStyle.SolidPattern)

        # Set the grid line color and thickness
        # convert self.settings_manager.settings.canvas_color.get() to QColor
        self.grid_pen = QPen(
            QColor(self.settings_manager.settings.line_color.get()),
            self.settings_manager.settings.line_width.get()
        )

        # Set the initial position for mouse dragging
        self.drag_pos = QPoint(0, 0)

        self.set_canvas_color()

    def update_grid_pen(self):
        self.grid_pen = QPen(
            QColor(self.settings_manager.settings.line_color.get()),
            self.settings_manager.settings.line_width.get()
        )
        self.update()

    def image_handler_old(self, active_img, data):
        action = data["action"]
        rect: QRect = data["options"]["outpaint_box_rect"]
        rect: QRect = data["options"]["outpaint_box_rect"]
        x = rect.x()
        y = rect.y()
        if len(self.current_layer.images) > 0:
            # merge with previous image
            image = self.current_layer.images[0].image
            image.paste(active_img, (int(x), int(y)))
            self.current_layer.images = [ImageData(QPoint(int(x), int(y)), image)]
        else:
            self.current_layer.images = [ImageData(QPoint(int(x), int(y)), active_img)]
        self.current_layer.lines = []
        self.update()

    def image_handler(self, active_img, data):
        self.update_image_canvas(data["action"], data, active_img)
        self.current_layer.lines = []
        self.update()

    def update_image_canvas(self, section=None, data=None, processed_image: Image = None):
        """
        Update the image by section
        This is used by other classes to add an image to the canvas
        :param section: the section (action) that was taken to generate this image. section is a deprecated name
        :param data: the data to update the image with
        :param processed_image: the image to update the canvas with
        :return:
        """
        processed_image = processed_image.convert("RGBA")
        section = data["action"] if not section else section
        outpaint_box_rect = data["options"]["outpaint_box_rect"]
        processed_image, image_root_point, image_pivot_point = self.handle_outpaint(
            outpaint_box_rect, processed_image, section
        )
        history_event = {
            "event": "set_image",
            "layer_index": self.current_layer_index,
            "images": self.current_layer.images,
            "previous_image_root_point": self.image_root_point,
            "previous_image_pivot_point": self.image_pivot_point,
        }
        self.parent.history.add_event(history_event)
        self.image_root_point = image_root_point
        self.image_pivot_point = image_pivot_point
        self.current_layer.images = [ImageData(image_pivot_point, processed_image)]

    def handle_outpaint(self, outpaint_box_rect, outpainted_image, action):
        if len(self.current_layer.images) == 0:
            point = QPoint(outpaint_box_rect.x(), outpaint_box_rect.y())
            return outpainted_image, self.image_root_point, point

        # make a copy of the current canvas image
        existing_image_copy = self.current_layer.images[0].image.copy()
        width = existing_image_copy.width
        height = existing_image_copy.height
        working_width = self.settings_manager.settings.working_width.get()
        working_height = self.settings_manager.settings.working_height.get()

        is_drawing_left = outpaint_box_rect.x() < self.image_pivot_point.x()
        is_drawing_up = outpaint_box_rect.y() < self.image_pivot_point.y()

        if is_drawing_left:
            # get the x overlap of the outpaint box and the image
            x_overlap = min(width, outpaint_box_rect.width()) - max(0, outpaint_box_rect.x())
        else:
            # get the x overlap of the outpaint box and the image
            x_overlap = min(width, outpaint_box_rect.width()) - max(0, outpaint_box_rect.x() - self.image_pivot_point.x())

        if is_drawing_up:
            # get the y overlap of the outpaint box and the image
            y_overlap = min(height, outpaint_box_rect.height()) - max(0, outpaint_box_rect.y())
        else:
            # get the y overlap of the outpaint box and the image
            y_overlap = min(height, outpaint_box_rect.height()) - max(0, outpaint_box_rect.y() - self.image_pivot_point.y())

        # get the x and y overlap of the outpaint box and the image
        new_dimensions = (int(width + working_width - x_overlap), int(height + working_height - y_overlap))
        if new_dimensions[0] < width:
            new_dimensions = (width, new_dimensions[1])
        if new_dimensions[1] < height:
            new_dimensions = (new_dimensions[0], height)
        new_image = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        new_image_a = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        new_image_b = Image.new("RGBA", new_dimensions, (0, 0, 0, 0))
        existing_image_pos = [0, 0]
        image_root_point = QPoint(self.image_root_point.x(), self.image_root_point.y())
        image_pivot_point = QPoint(self.image_pivot_point.x(), self.image_pivot_point.y())
        if is_drawing_left:
            current_x_pos = abs(outpaint_box_rect.x() - image_pivot_point.x())
            left_overlap = abs(outpaint_box_rect.x()) - abs(image_root_point.x())
            image_root_point.setX(width + left_overlap)
            image_pivot_point.setX(int(outpaint_box_rect.x()))
            existing_image_pos = [current_x_pos, existing_image_pos[1]]
            pos_x = max(0, outpaint_box_rect.x() + self.image_pivot_point.x())
        else:
            pos_x = max(0, outpaint_box_rect.x() - self.image_pivot_point.x())
        if is_drawing_up:
            current_y_pos = abs(outpaint_box_rect.y() - image_pivot_point.y())
            up_overlap = abs(outpaint_box_rect.y()) - abs(image_root_point.y())
            image_root_point.setY(height + up_overlap)
            image_pivot_point.setY(int(outpaint_box_rect.y()))
            existing_image_pos = [existing_image_pos[0], current_y_pos]
            pos_y = max(0, outpaint_box_rect.y() + self.image_pivot_point.y())
        else:
            pos_y = max(0, outpaint_box_rect.y() - self.image_pivot_point.y())

        new_image_a.paste(outpainted_image, (int(pos_x), int(pos_y)))
        new_image_b.paste(existing_image_copy, (int(existing_image_pos[0]), int(existing_image_pos[1])))

        if action == "outpaint":
            new_image = Image.alpha_composite(new_image, new_image_a)
            new_image = Image.alpha_composite(new_image, new_image_b)
        else:
            new_image = Image.alpha_composite(new_image, new_image_b)
            new_image = Image.alpha_composite(new_image, new_image_a)

        return new_image, image_root_point, image_pivot_point

    def set_canvas_color(self):
        self.canvas_container.setStyleSheet(f"background-color: {self.settings_manager.settings.canvas_color.get()};")
        self.canvas_container.setAutoFillBackground(True)

    def paintEvent(self, event):
        # Draw the grid and any lines that have been drawn by the user
        painter = QPainter(self.canvas_container)

        # draw grid
        if not self.saving:
            self.draw_grid(painter)

        layers = self.layers.copy()
        layers.reverse()
        for index in range(len(layers)):
            layer = layers[index]
            if not layer.visible:
                continue
            # draw image
            self.draw_images(layer, index, painter)

            # draw user lines
            self.draw_user_lines(layer, index, painter)

            # draw widgets
            self.draw_widgets(layer, index, painter)

        self.draw_selection_box(painter)

        if not self.saving:
            self.draw_active_grid_area_container(painter)

    def enter_event(self, event):
        self.update_cursor()

    def update_cursor(self):
        if self.brush_selected or self.eraser_selected:
            self.canvas_container.setCursor(Qt.CursorShape.CrossCursor)
        elif self.move_selected:
            self.canvas_container.setCursor(Qt.CursorShape.OpenHandCursor)
        elif self.active_grid_area_selected:
            self.canvas_container.setCursor(Qt.CursorShape.DragMoveCursor)
        else:
            self.canvas_container.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def leave_event(self, event):
        self.canvas_container.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def update(self):
        self.canvas_container.update()

    def draw_grid(self, painter):
        if not self.settings_manager.settings.show_grid.get():
            return

        # Define the starting and ending coordinates for the grid lines
        start_x = self.pos_x % self.grid_size
        end_x = self.canvas_container.width()
        start_y = self.pos_y % self.grid_size
        end_y = self.canvas_container.height()

        line_width = self.settings_manager.settings.line_width.get()
        self.grid_pen.setWidth(line_width)
        # Draw horizontal grid lines
        y = start_y
        while y < end_y:
            painter.setPen(self.grid_pen)
            painter.drawLine(0, y, self.canvas_container.width(), y)
            y += self.grid_size

        # Draw vertical grid lines
        x = start_x
        while x < end_x:
            painter.setPen(self.grid_pen)
            painter.drawLine(x, 0, x, self.canvas_container.height())
            x += self.grid_size

    def draw_active_grid_area_container(self, painter):
        """
        Draw a rectangle around the active grid area of
        """
        painter.setPen(self.grid_pen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        pen = QPen(
            self.active_grid_area_color,
            self.settings_manager.settings.line_width.get()
        )
        painter.setPen(pen)
        rect = QRect(
            self.active_grid_area_rect.x(),
            self.active_grid_area_rect.y(),
            self.settings_manager.settings.working_width.get(),
            self.settings_manager.settings.working_height.get()
        )
        painter.drawRect(rect)

    def create_image(self, location, image):
        """
        Create a new image object and add it to the current layer
        """
        # convert image to RGBA
        image = image.convert("RGBA")
        self.current_layer.images.append(ImageData(location, image))

    ######
    # Drawing functions: render images, widgets and lines to canvas
    ######
    def draw_images(self, layer, index, painter):
        for image in layer.images:
            # display PIL.image as QPixmap
            img = image.image
            if self.parent.current_filter and index == self.current_layer_index:
                img = img.filter(self.parent.current_filter)
            qimage = ImageQt(img)
            pixmap = QPixmap.fromImage(qimage)

            # apply the layer offset
            x = image.position.x() + self.pos_x
            y = image.position.y() + self.pos_y
            location = QPoint(int(x), int(y)) + self.current_layer.offset

            # draw the image
            painter.drawPixmap(location, pixmap)

    def draw_widgets(self, layer, index, painter):
        for widget in layer.widgets:
            widget.draw(painter)

    def draw_user_lines(self, layer, index, painter):
        painter.setBrush(self.brush)
        for line in layer.lines:
            pen = line.pen
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            start = QPointF(line.start_point.x() + self.pos_x, line.start_point.y() + self.pos_y)
            end = QPointF(line.end_point.x() + self.pos_x, line.end_point.y() + self.pos_y)

            # also apply the layer offset
            offset = QPointF(self.current_layer.offset.x(), self.current_layer.offset.y())
            start += offset
            end += offset

            # create a QPainterPath to hold the curve
            path = QPainterPath()
            path.moveTo(QPointF(start.x(), start.y()))

            # calculate control points for the Bezier curve
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            ctrl1 = QPointF(start.x() + dx / 3, start.y() + dy / 3)
            ctrl2 = QPointF(end.x() - dx / 3, end.y() - dy / 3)

            # add the curve to the path
            path.cubicTo(ctrl1, ctrl2, end)

            # create a QPolygonF from the path to draw the curve
            polygons = path.toSubpathPolygons()
            if len(polygons) > 0:
                curve = QPolygonF(polygons[0])
                painter.drawPolyline(curve)
    ######
    # End Drawing functions
    ######

    def invert_image(self):
        # convert image mode to RGBA
        for image in self.current_layer.images:
            image.image = image.image.convert("RGB")
            image.image = ImageOps.invert(image.image)
            image.image = image.image.convert("RGBA")

    def draw_selection_box(self, painter):
        if self.select_start is not None and self.select_end is not None:
            # the rectangle should have a dashed line border
            painter.setPen(QPen(Qt.GlobalColor.red, 1))
            painter.setBrush(Qt.GlobalColor.transparent)
            painter.drawRect(QRect(self.select_start, self.select_end))

    def load_image(self, image_path):
        image = Image.open(image_path)

        # if settings_manager.settings.resize_on_paste, resize the image to working width and height while mainting its aspect ratio
        if self.settings_manager.settings.resize_on_paste.get():
            image.thumbnail((self.settings_manager.settings.working_width.get(), self.settings_manager.settings.working_height.get()), Image.ANTIALIAS)

        self.create_image(QPoint(0, 0), image)
        self.update()

    def save_image(self, image_path):
        image = self.current_layer.image.image
        image = image.convert("RGBA")
        image.save(image_path)
        self.saving = False
        self.update()

    def clear(self):
        self.current_layer.lines = []
        self.current_layer.images = []
        self.update()

    def recenter(self):
        self.pos_x = 0
        self.pos_y = 0
        self.update()

    def handle_erase(self, event):
        self.is_erasing = True
        # Erase any line segments that intersect with the current position of the mouse
        brush_size = self.settings_manager.settings.mask_brush_size.get()
        start = event.pos() - QPoint(self.pos_x, self.pos_y) - self.image_pivot_point
        for i, line in enumerate(self.current_layer.lines):
            # check if line intersects with start using brush size radius
            if line.intersects(start, brush_size):
                self.current_layer.lines.pop(i)
                self.update()

        # erase pixels from image
        if len(self.current_layer.images) > 0:
            image = self.current_layer.images[0].image
            if image:
                image = image.copy()
                draw = ImageDraw.Draw(image)
                draw.ellipse((start.x() - brush_size, start.y() - brush_size, start.x() + brush_size, start.y() + brush_size), fill=(0, 0, 0, 0))
                self.current_layer.images[0].image = image
                self.update()


        self.update()

    def copy_image(self):
        im = self.current_active_image
        if not im:
            return
        output = io.BytesIO()
        if self.parent.is_windows:
            im.save(output, format="DIB")
            self.image_to_system_clipboard_windows(output.getvalue())
        else:
            im.save(output, format="PNG")
            self.image_to_system_clipboard_linux(output.getvalue())

    def image_to_system_clipboard_windows(self, data):
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

    def image_to_system_clipboard_linux(self, data):
        try:
            subprocess.Popen(["xclip", "-selection", "clipboard", "-t", "image/png"],
                             stdin=subprocess.PIPE).communicate(data)
        except FileNotFoundError:
            pass

    def image_to_system_clipboard_windows(self, data):
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

    def image_from_system_clipboard_windows(self):
        try:
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
            win32clipboard.CloseClipboard()
            # convert bytes to image
            image = Image.open(io.BytesIO(data))
            return image
        except Exception as e:
            ErrorWindow(message=str(e))
            return None

    def image_from_system_clipboard_linux(self):
        try:
            image = ImageGrab.grabclipboard()
            # with transparency
            image = image.convert("RGBA")
            return image
        except Exception as e:
            return None

    def paste_image_from_clipboard(self):
        if self.parent.is_windows:
            image = self.image_from_system_clipboard_windows()
        else:
            image = self.image_from_system_clipboard_linux()

        if not image:
            return

        if self.settings_manager.settings.resize_on_paste.get():
            if self.settings_manager.settings.resize_on_paste.get():
                image.thumbnail((self.settings_manager.settings.working_width.get(),
                                 self.settings_manager.settings.working_height.get()), Image.ANTIALIAS)
        self.create_image(QPoint(0, 0), image)

    def pen(self, event):
        if event.button() == Qt.MouseButton.LeftButton or Qt.MouseButton.LeftButton in event.buttons():
            brush_color = self.settings_manager.settings.primary_color.get()
        elif event.button() == Qt.MouseButton.RightButton or Qt.MouseButton.RightButton in event.buttons():
            brush_color = self.settings_manager.settings.secondary_color.get()
        brush_color = QColor(brush_color)
        return QPen(
            brush_color,
            self.settings_manager.settings.mask_brush_size.get()
        )

    def handle_draw(self, event):
        # Continue drawing the current line as the mouse is moved but use brush_size
        # to control the radius of the line being drawn
        start = event.pos() - QPoint(self.pos_x, self.pos_y)
        pen = self.pen(event)
        if len(self.current_layer.lines) > 0:
            previous = LineData(self.current_layer.lines[-1].start_point, start, pen, self.current_layer_index)
            self.current_layer.lines[-1] = previous
        end = event.pos() - QPoint(self.pos_x, self.pos_y)
        line_data = LineData(start, end, pen, self.current_layer_index)
        self.current_layer.lines.append(line_data)
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
            rect = rect.united(QRect(self.current_layer.images[0].position.x(), self.current_layer.images[0].position.y(), self.current_layer.images[0].image.size[0], self.current_layer.images[0].image.size[1]))
        except IndexError:
            pass

        # center the point on the rect
        point.setX(int(point.x() - int(rect.width() / 2)))
        point.setY(int(point.y() - int(rect.height() / 2)))

        self.layers[self.current_layer_index].offset = point

    def mouse_press_event(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.select_start = event.pos()
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            if self.brush_selected:
                self.parent.history.add_event({
                    "event": "draw",
                    "layer_index": self.current_layer_index,
                    "lines": self.current_layer.lines.copy()
                })
                self.start_drawing_line_index = len(self.current_layer.lines)
                start = event.pos() - QPoint(self.pos_x, self.pos_y)
                end = event.pos() - QPoint(self.pos_x, self.pos_y)
                pen = self.pen(event)
                line = LineData(start, end, pen, self.current_layer_index)
                start += self.layers[self.current_layer_index].offset
                end += self.layers[self.current_layer_index].offset
                self.current_layer.lines += [line]
            self.handle_tool(event)
            self.update()
        elif event.button() == Qt.MouseButton.MiddleButton:
            # Start dragging the canvas when the middle or right mouse button is pressed
            self.drag_pos = event.pos()

    def mouse_move_event(self, event):
        # check if LeftButton is pressed
        if Qt.MouseButton.LeftButton in event.buttons() or Qt.MouseButton.RightButton in event.buttons():
            self.handle_tool(event)
            self.update()
        elif self.drag_pos is not None:
            self.handle_move_canvas(event)

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

    def get_image_copy(self, index):
        return [ImageData(imageData.position, imageData.image.copy()) for imageData in self.layers[index].images]

    def handle_tool(self, event):
        if self.eraser_selected:
            if not self.is_erasing:
                self.parent.history.add_event({
                    "event": "erase",
                    "layer_index": self.current_layer_index,
                    "lines": self.current_layer.lines.copy(),
                    "images": self.get_image_copy(self.current_layer_index)
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

    def mouse_release_event(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            if self.brush_selected:
                self.stop_drawing_line_index = len(self.current_layer.lines)
                self.update()
            elif self.eraser_selected:
                self.is_erasing = False
        elif event.button() == Qt.MouseButton.MiddleButton:
            # Start dragging the canvas when the middle or right mouse button is pressed
            self.drag_pos = event.pos()
