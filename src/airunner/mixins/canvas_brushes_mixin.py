from PIL import ImageDraw
from PyQt6.QtCore import Qt, QPointF, QPoint, QSize, QRect
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QImage
from airunner.models.linedata import LineData
from airunner.models.imagedata import ImageData
from PIL import Image


class CanvasBrushesMixin:
    _point = None
    active_canvas_rect = QRect(0, 0, 0, 0)
    opacity = None
    color = None
    width = None
    
    @property
    def is_drawing(self):
        return self.left_mouse_button_down or self.right_mouse_button_down

    @property
    def primary_color(self):
        return QColor(self.settings_manager.settings.primary_color.get())

    @property
    def primary_brush_opacity(self):
        return self.settings_manager.settings.primary_brush_opacity.get()

    @property
    def secondary_color(self):
        return QColor(self.settings_manager.settings.secondary_color.get())

    @property
    def secondary_brush_opacity(self):
        return self.settings_manager.settings.secondary_brush_opacity.get()

    def draw(self, layer, index):
        path = QPainterPath()
        painter = None
        for line in layer.lines:
            pen = line.pen
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            if self.width is None or self.width != line.width:
                self.width = line.width
                self.draw_path(path, painter)
                painter = None
            if self.color is None or self.color != line.color:
                self.color = line.color
                self.draw_path(path, painter)
                painter = None
            if self.opacity is None or self.opacity != line.opacity:
                self.opacity = line.opacity
                self.draw_path(path, painter)
                painter = None
            if not painter:
                painter = QPainter(self.canvas_container)
                painter.setBrush(self.brush)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
            painter.setPen(pen)
            painter.setOpacity(line.opacity / 255)

            start = QPointF(line.start_point.x() + self.pos_x, line.start_point.y() + self.pos_y)
            end = QPointF(line.end_point.x() + self.pos_x, line.end_point.y() + self.pos_y)

            # also apply the layer offset
            offset = QPointF(self.current_layer.offset.x(), self.current_layer.offset.y())
            start += offset
            end += offset

            # calculate control points for the Bezier curve
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            ctrl1 = QPointF(start.x() + dx / 3, start.y() + dy / 3)
            ctrl2 = QPointF(end.x() - dx / 3, end.y() - dy / 3)

            # add the curve to the path
            path.moveTo(start)
            path.cubicTo(ctrl1, ctrl2, end)

        # draw the entire line with a single drawPath call
        self.draw_path(path, painter)

    def draw_path(self, path, painter):
        if painter:
            painter.drawPath(path)
            painter.end()

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

    def pen(self, event):
        brush_color = "#ffffff"
        if event.button() == Qt.MouseButton.LeftButton or Qt.MouseButton.LeftButton in event.buttons():
            brush_color = self.settings_manager.settings.primary_color.get()
        elif event.button() == Qt.MouseButton.RightButton or Qt.MouseButton.RightButton in event.buttons():
            brush_color = self.settings_manager.settings.secondary_color.get()
        brush_color = QColor(brush_color)
        pen = QPen(
            brush_color,
            self.settings_manager.settings.mask_brush_size.get()
        )
        return pen

    def handle_draw(self, event):
        start = event.pos() - QPoint(self.pos_x, self.pos_y)
        pen = self.pen(event)
        opacity = 255
        if event.button() == Qt.MouseButton.LeftButton or Qt.MouseButton.LeftButton in event.buttons():
            opacity = self.primary_brush_opacity
        elif event.button() == Qt.MouseButton.RightButton or Qt.MouseButton.RightButton in event.buttons():
            opacity = self.secondary_brush_opacity
        if len(self.current_layer.lines) > 0:
            previous = LineData(self.current_layer.lines[-1].start_point, start, pen, self.current_layer_index, opacity)
            self.current_layer.lines[-1] = previous

            if self.shift_is_pressed:  # draw a strait line by combining the line segments
                if len(self.current_layer.lines) > self.start_drawing_line_index:
                    start_line = self.current_layer.lines[self.start_drawing_line_index]
                    end_line = self.current_layer.lines[self.stop_drawing_line_index - 1]
                    new_line_data = LineData(
                        start_line.start_point,
                        end_line.end_point,
                        start_line.pen,
                        start_line.layer_index,
                        start_line.opacity
                    )
                    self.current_layer.lines = self.current_layer.lines[:self.start_drawing_line_index]
                    self.current_layer.lines.append(new_line_data)

        end = event.pos() - QPoint(self.pos_x + 1, self.pos_y)
        line_data = LineData(start, end, pen, self.current_layer_index, opacity)
        self.current_layer.lines.append(line_data)
        self.update()

    left_line_extremity = 0
    right_line_extremity = 0
    top_line_extremity = 0
    bottom_line_extremity = 0
    max_left = 0
    max_top = 0
    max_right = 0
    max_bottom = 0
    last_left = 0
    last_top = 0

    def get_line_extremities(self):
        for line in self.current_layer.lines:
            start_x = line.start_point.x()
            start_y = line.start_point.y()
            end_x = line.end_point.x()
            end_y = line.end_point.y()
            if self.left_line_extremity is None or start_x < self.left_line_extremity:
                self.left_line_extremity = start_x
            if self.right_line_extremity is None or start_x > self.right_line_extremity:
                self.right_line_extremity = start_x
            if self.top_line_extremity is None or start_y < self.top_line_extremity:
                self.top_line_extremity = start_y
            if self.bottom_line_extremity is None or start_y > self.bottom_line_extremity:
                self.bottom_line_extremity = start_y
            if end_x < self.left_line_extremity:
                self.left_line_extremity = end_x
            if end_x > self.right_line_extremity:
                self.right_line_extremity = end_x
            if end_y < self.top_line_extremity:
                self.top_line_extremity = end_y
            if end_y > self.bottom_line_extremity:
                self.bottom_line_extremity = end_y
        if self.top_line_extremity > -self.pos_y:
            self.top_line_extremity = -self.pos_y
        if self.left_line_extremity > -self.pos_x:
            self.left_line_extremity = -self.pos_x
        brush_size = self.settings_manager.settings.mask_brush_size.get()
        return self.top_line_extremity - brush_size, self.left_line_extremity - brush_size, self.bottom_line_extremity + brush_size, self.right_line_extremity + brush_size

    def rasterize_lines(self):
        if len(self.current_layer.lines) == 0:
            return
        top, left, bottom, right = self.get_line_extremities()

        left = min(self.max_left, left)
        top = min(self.max_top, top)
        right = max(self.max_right, right)
        bottom = max(self.max_bottom, bottom)

        # create a QImage with the size of the lines
        brush_size = self.settings_manager.settings.mask_brush_size.get()
        width = brush_size + right - left
        height = brush_size + bottom - top
        img = QImage(QSize(width, height), QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        painter.setBrush(self.brush)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = self.create_image_path(painter)
        painter.drawPath(path)
        painter.end()
        self.convert_pixmap_to_pil_image(img, top, left, bottom, right)

    def create_image_path(self, painter):
        path = QPainterPath()
        for line in self.current_layer.lines:
            pen = line.pen
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

            painter.setPen(pen)
            painter.setOpacity(line.opacity / 255)

            start = QPointF(line.start_point.x() + self.pos_x, line.start_point.y() + self.pos_y)
            end = QPointF(line.end_point.x() + self.pos_x, line.end_point.y() + self.pos_y)

            # also apply the layer offset
            offset = QPointF(self.current_layer.offset.x(), self.current_layer.offset.y())
            start += offset
            end += offset

            # calculate control points for the Bezier curve
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            ctrl1 = QPointF(start.x() + dx / 3, start.y() + dy / 3)
            ctrl2 = QPointF(end.x() - dx / 3, end.y() - dy / 3)

            # add the curve to the path
            path.moveTo(start)
            path.cubicTo(ctrl1, ctrl2, end)
        return path

    def convert_pixmap_to_pil_image(self, img: Image, top: int, left: int, bottom: int, right: int):
        self.max_left = left if left < self.max_left else self.max_left
        self.max_top = top if top < self.max_top else self.max_top
        self.max_right = right if right > self.max_right else self.max_right
        self.max_bottom = bottom if bottom > self.max_bottom else self.max_bottom

        img = Image.fromqpixmap(img)
        current_image = self.current_layer.images[0].image.copy() if len(self.current_layer.images) > 0 else None
        width = abs(right) + abs(left)
        height = abs(bottom) + abs(top)
        existing_image_width = current_image.width if current_image else 0
        existing_image_height = current_image.height if current_image else 0

        composite_width = existing_image_width if existing_image_width > width else width
        composite_height = existing_image_height if existing_image_height > height else height

        if composite_width < (self.max_right - self.max_left):
            composite_width = self.max_right - self.max_left
        if composite_height < (self.max_bottom - self.max_top):
            composite_height = self.max_bottom - self.max_top

        composite_image = Image.new('RGBA', (composite_width, composite_height), (0, 0, 0, 0))

        q_point_x = self.max_left
        q_point_y = self.max_top
        composite_img_dest = QPoint(q_point_x, q_point_y)

        pos_x = 0
        pos_y = 0

        if self.last_left != self.max_left:
            last_left = self.last_left
            self.last_left = self.max_left
            pos_x = -self.last_left + last_left
        if self.last_top != self.max_top:
            last_top = self.last_top
            self.last_top = self.max_top
            pos_y = -self.last_top + last_top

        new_img_dest_pos_x = -(self.pos_x - abs(left))
        new_img_dest_pos_y = -(self.pos_y - abs(top))

        # self.parent.window.debug_label.setText(
        #     f"W/H: {width}x{height} | imgdest: {new_img_dest_pos_x}, {new_img_dest_pos_y} | ext: {self.left_line_extremity}, {self.top_line_extremity}, {self.right_line_extremity}, {self.bottom_line_extremity} | max: {self.max_left}, {self.max_top} {self.max_right} {self.max_bottom} | last: {self.last_left}, {self.last_top}"
        # )

        # add current image to the composite image
        if current_image:
            existing_img_dest = (pos_x, pos_y)
            existing_img_source = (0, 0)
            composite_image.alpha_composite(current_image, existing_img_dest, existing_img_source)
        new_img_dest = (new_img_dest_pos_x, new_img_dest_pos_y)
        composite_image.alpha_composite(img, new_img_dest)
        self.add_image_to_canvas_new(composite_image, composite_img_dest, self.image_root_point)
        self.current_layer.lines.clear()

