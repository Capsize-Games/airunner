from PIL import ImageDraw
from PyQt6.QtCore import Qt, QPointF, QPoint, QSize, QRect
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QImage
from airunner.models.linedata import LineData
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
        brush_size = int(self.settings_manager.settings.mask_brush_size.get() / 2)
        start = event.pos() - QPoint(self.pos_x, self.pos_y)
        image = self.current_layer.images[0].image if len(self.current_layer.images) > 0 else None
        image_pos = self.current_layer.images[0].position if len(self.current_layer.images) > 0 else None
        start -= image_pos
        if image:
            image = image.copy()
            draw = ImageDraw.Draw(image)
            draw.ellipse((
                start.x() - brush_size,
                start.y() - brush_size,
                start.x() + brush_size,
                start.y() + brush_size
            ), fill=(0, 0, 0, 0))
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

    left_line_extremity = None
    right_line_extremity = None
    top_line_extremity = None
    bottom_line_extremity = None
    last_left = 0
    last_top = 0
    min_x = 0
    min_y = 0


    def get_line_extremities(self):
        for line in self.current_layer.lines:
            start_x = line.start_point.x()
            start_y = line.start_point.y()
            end_x = line.end_point.x()
            end_y = line.end_point.y()

            brush_size = int(self.settings_manager.settings.mask_brush_size.get() / 2)
            min_x = min(start_x, end_x) - brush_size
            min_y = min(start_y, end_y) - brush_size
            max_x = max(start_x, end_x) + brush_size
            max_y = max(start_y, end_y) + brush_size
            self.min_x = min_x
            self.min_y = min_y

            image = self.current_layer.images[0].image if len(self.current_layer.images) > 0 else None
            if image:
                position = self.current_layer.images[0].position
                min_x = min(min_x, position.x())
                min_y = min(min_y, position.y())
                max_x = max(max_x, image.width)
                max_y = max(max_y, image.height)

            if self.left_line_extremity is None or min_x < self.left_line_extremity:
                self.left_line_extremity = min_x
            if self.right_line_extremity is None or max_x > self.right_line_extremity:
                self.right_line_extremity = max_x
            if self.top_line_extremity is None or min_y < self.top_line_extremity:
                self.top_line_extremity = min_y
            if self.bottom_line_extremity is None or max_y > self.bottom_line_extremity:
                self.bottom_line_extremity = max_y
        return self.top_line_extremity, self.left_line_extremity, self.bottom_line_extremity, self.right_line_extremity

    def rasterize_lines(self):
        if len(self.current_layer.lines) == 0:
            return
        top, left, bottom, right = self.get_line_extremities()

        # create a QImage with the size of the lines
        min_x = min(left, right)
        min_y = min(top, bottom)
        max_x = max(left, right)
        max_y = max(top, bottom)
        width = abs(max_x - min_x)
        height = abs(max_y - min_y)
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

            start = QPointF(line.start_point.x() - self.left_line_extremity, line.start_point.y() - self.top_line_extremity)
            end = QPointF(line.end_point.x() - self.left_line_extremity, line.end_point.y() - self.top_line_extremity)

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
        img = Image.fromqpixmap(img)
        width = img.width
        height = img.height
        current_image = self.current_layer.images[0].image.copy() if len(self.current_layer.images) > 0 else None
        existing_image_width = current_image.width if current_image else 0
        existing_image_height = current_image.height if current_image else 0

        composite_width = width
        composite_height = height
        if existing_image_width > composite_width:
            composite_width = existing_image_width
        if existing_image_height > composite_height:
            composite_height = existing_image_height

        composite_image = Image.new('RGBA', (composite_width, composite_height), (0, 0, 0, 0))
        composite_img_dest = QPoint(left, top)

        pos_x = 0
        pos_y = 0

        if self.last_left != left:
            last_left = self.last_left
            self.last_left = left
            pos_x = -self.last_left + last_left
        if self.last_top != top:
            last_top = self.last_top
            self.last_top = top
            pos_y = -self.last_top + last_top

        new_img_dest_pos_x = 0
        new_img_dest_pos_y = 0

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

