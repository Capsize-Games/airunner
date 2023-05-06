from PIL import ImageDraw
from PyQt6.QtCore import Qt, QPointF, QPoint, QSize, QRect
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QImage
from airunner.models.linedata import LineData
from PIL import Image


class CanvasBrushesMixin:
    _point = None
    active_canvas_rect = QRect(0, 0, 0, 0)

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
        left = 0
        right = 0
        top = 0
        bottom = 0
        for line in self.current_layer.lines:
            start_x = line.start_point.x()
            start_y = line.start_point.y()
            end_x = line.end_point.x()
            end_y = line.end_point.y()
            if start_x < left:
                left = start_x
            if start_x > right:
                right = start_x
            if start_y < top:
                top = start_y
            if start_y > bottom:
                bottom = start_y
            if end_x < left:
                left = end_x
            if end_x > right:
                right = end_x
            if end_y < top:
                top = end_y
            if end_y > bottom:
                bottom = end_y
        # if len(self.current_layer.images) > 0:
        #     image = self.current_layer.images[0].image
        #     image_width, image_height = image.size
        #     if image_width > right - left:
        #         right = image_width
        #     if image_height > bottom - top:
        #         bottom = image_height
        brush_size = self.settings_manager.settings.mask_brush_size.get()
        return top-brush_size, left-brush_size, bottom + brush_size, right + brush_size

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

    max_left = 0
    max_top = 0
    max_right = 0
    max_bottom = 0

    def convert_pixmap_to_pil_image(self, img, top, left, bottom, right):
        new_image = Image.fromqpixmap(img)
        existing_image = None
        self.active_canvas_rect = QRect(left, top, right, bottom)
        if len(self.current_layer.images) > 0:
            existing_image = self.current_layer.images[0].image.copy()
        width, height = self.rasterized_lines_image_size(new_image, existing_image)
        point = QPoint(0, 0)
        pos = (-self.pos_x, -self.pos_y)
        if self.pos_x > 0:
            # pos = (self.pos_x, pos[1])
            point.setX(-self.pos_x)
        if self.pos_y > 0:
            pos = (pos[0], self.pos_y)
            point.setY(-self.pos_y)
        new_width = width
        new_height = height

        if self.pos_x > 0 and self.pos_x > self.max_left:
            new_width = width + self.pos_x - self.max_left
            self.max_left = self.pos_x
        if self.pos_y > 0 and self.pos_y > self.max_top:
            new_height = height + self.pos_y - self.max_top
            self.max_top = self.pos_y
        if self.pos_x < 0 and abs(self.pos_x) > self.max_right:
            self.max_right = abs(self.pos_x)
        if self.pos_y < 0 and abs(self.pos_y) > self.max_bottom:
            self.max_bottom = abs(self.pos_y)

        composite_image = Image.new("RGBA", (new_width, new_height), (255, 0, 0, 255))

        # show debug info
        self.parent.window.debug_label.setText(
            f"rect ({left}, {top}, {right}, {bottom}) | point: {point.x()}, {point.y()} | pos: {pos[0]}, {pos[1]} | size: {width}, {height}"
        )

        if existing_image:
            composite_image.alpha_composite(existing_image, (0, 0))
        composite_image.alpha_composite(new_image, pos)
        self.current_layer.lines.clear()
        self.add_image_to_canvas_new(composite_image, point, self.image_root_point)

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
