from PIL import ImageDraw
from PyQt6.QtCore import Qt, QPointF, QPoint, QSize
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QImage
from airunner.models.linedata import LineData
from PIL import Image


class CanvasBrushesMixin:
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
        # in order to get the size of the image we need to determine the left, right, top and bottom most points
        # of the lines
        left = 0
        right = 0
        top = 0
        bottom = 0
        for line in self.current_layer.lines:
            start = line.start_point
            end = line.end_point
            if start.x() < left:
                left = start.x()
            if start.x() > right:
                right = start.x()
            if start.y() < top:
                top = start.y()
            if start.y() > bottom:
                bottom = start.y()
            if end.x() < left:
                left = end.x()
            if end.x() > right:
                right = end.x()
            if end.y() < top:
                top = end.y()
            if end.y() > bottom:
                bottom = end.y()

        # if the layer has an image, we need to determine if the image is larger than the lines
        if len(self.current_layer.images) > 0:
            image = self.current_layer.images[0].image
            image_width, image_height = image.size
            if image_width > right - left:
                right = image_width
            if image_height > bottom - top:
                bottom = image_height
        return top, left, bottom, right

    def rasterize_lines(self):
        if len(self.current_layer.lines) == 0:
            return
        top, left, bottom, right = self.get_line_extremities()
        # create a QImage with the size of the lines
        img = QImage(QSize(right - left, bottom - top), QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        painter.setBrush(self.brush)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = self.create_image_path(painter)
        painter.drawPath(path)
        painter.end()
        self.convert_pixmap_to_pil_image(img)

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

    def convert_pixmap_to_pil_image(self, img):
        # convert to PIL Image
        pil_image = Image.fromqpixmap(img)
        current_image_width = 0
        current_image_height = 0
        existing_image = None

        if len(self.current_layer.images) > 0:
            current_image_width = self.current_layer.images[0].image.width
            current_image_height = self.current_layer.images[0].image.height
            existing_image = self.current_layer.images[0].image.copy()

        width = pil_image.width if pil_image.width > current_image_width else current_image_width
        height = pil_image.height if pil_image.height > current_image_height else current_image_height
        composite_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        if existing_image:
             composite_image.paste(existing_image, (0, 0))

        composite_image.alpha_composite(pil_image, (-self.pos_x, -self.pos_y))
        pil_image = composite_image
        self.current_layer.lines.clear()
        self.add_image_to_canvas(pil_image)

    def handle_erase(self, event):
        self.is_erasing = True
        # Erase any line segments that intersect with the current position of the mouse
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
