from PIL import ImageDraw
from PyQt6.QtCore import Qt, QPointF, QPoint, QSize, QRect
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QImage
from airunner.models.linedata import LineData
from PIL import Image


class CanvasBrushesMixin:
    _point = None
    active_canvas_rect = QRect(0, 0, 0, 0)
    left_line_extremity = None
    right_line_extremity = None
    top_line_extremity = None
    bottom_line_extremity = None
    max_left = 0
    max_top = 0
    max_right = 0
    max_bottom = 0
    last_left = None
    last_top = None

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
        painter = QPainter(self.canvas_container)
        painter.setBrush(self.brush)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # create a QPainterPath to hold the entire line
        path = QPainterPath()
        if len(layer.lines) == 0:
            painter.end()
            return
        for line in layer.lines:
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

        # draw the entire line with a single drawPath call
        painter.drawPath(path)
        painter.end()

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
        # if len(self.current_layer.images) > 0:
        #     image = self.current_layer.images[0].image
        #     image_width, image_height = image.size
        #     if image_width > right - left:
        #         right = image_width
        #     if image_height > bottom - top:
        #         bottom = image_height
        brush_size = self.settings_manager.settings.mask_brush_size.get()
        return self.top_line_extremity - brush_size, self.left_line_extremity - brush_size, self.bottom_line_extremity + brush_size, self.right_line_extremity + brush_size

    def rasterize_lines(self):
        if len(self.current_layer.lines) == 0:
            return
        top, left, bottom, right = self.get_line_extremities()
        # create a QImage with the size of the lines
        img = QImage(QSize(right, bottom), QImage.Format.Format_ARGB32)
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

    def rasterized_lines_image_size(self, new_image, existing_image=None):
        width = new_image.width
        height = new_image.height
        if existing_image:
            if new_image.width < existing_image.width:
                width = existing_image.width
            if new_image.height < existing_image.height:
                height = existing_image.height
        if self.active_canvas_rect.width() > width:
            width = self.active_canvas_rect.width()
        if self.active_canvas_rect.height() > height:
            height = self.active_canvas_rect.height()
        return width, height

    def convert_pixmap_to_pil_image(self, img: Image, top: int, left: int, bottom: int, right: int):
        img = Image.fromqpixmap(img)
        current_image = None
        if len(self.current_layer.images) > 0:
            current_image = self.current_layer.images[0].image.copy()

        width = abs(right)
        height = abs(bottom)

        pos_x = 0 if (self.pos_x < 0 or self.pos_x == 0) else abs(self.pos_x)
        pos_y = 0 if (self.pos_y < 0 or self.pos_y == 0) else abs(self.pos_y)

        existing_image_width = 0
        existing_image_height = 0
        if current_image:
            existing_image_width = current_image.width
            existing_image_height = current_image.height

        composite_width = width
        composite_height = height

        if existing_image_height > composite_height:
            composite_height = existing_image_height
        if existing_image_width > composite_width:
            composite_width = existing_image_width

        composite_image = Image.new('RGBA', (composite_width, composite_height), (255, 0, 0, 255))

        if current_image:
            if not self.last_left or self.last_left != self.max_left:
                if self.last_left:
                    l = self.max_left - self.last_left
                    self.last_left = self.max_left
                else:
                    self.last_left = self.max_left
                    l = self.last_left
            else:
                l = 0
            if not self.last_top or self.last_top != self.max_top:
                if self.last_top:
                    t = self.max_top - self.last_top
                    self.last_top = self.max_top - self.last_top
                else:
                    self.last_top = self.max_top
                    t = self.last_top
            else:
                t = 0
            composite_image.alpha_composite(current_image, (l, t), (0, 0, existing_image_width, existing_image_height))
        composite_image.alpha_composite(img, (-self.pos_x, -self.pos_y))
        self.add_image_to_canvas_new(composite_image, QPoint(0, 0), self.image_root_point)
        self.current_layer.lines.clear()

    def handle_erase(self, event):
        self.is_erasing = True
        brush_size = self.settings_manager.settings.mask_brush_size.get()
        start = event.pos() - QPoint(self.pos_x, self.pos_y) - self.image_pivot_point
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
        # Continue drawing the current line as the mouse is moved but use brush_size
        # to control the radius of the line being drawn
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
        end = event.pos() - QPoint(self.pos_x, self.pos_y)
        line_data = LineData(start, end, pen, self.current_layer_index, opacity)
        self.current_layer.lines.append(line_data)
        self.update()
