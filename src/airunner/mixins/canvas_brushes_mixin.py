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