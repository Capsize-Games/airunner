from PIL import ImageDraw, ImageFilter, UnidentifiedImageError
from PyQt6.QtCore import Qt, QPointF, QPoint, QSize, QRect, QThread, QObject, pyqtSignal, QTimer, QRunnable, QThreadPool
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen, QImage
from airunner.models.layerdata import LayerData
from airunner.models.linedata import LineData
from PIL import Image


class RasterizationWorker(QObject):
    finished = pyqtSignal()

    def __init__(self, *args, **kwargs):
        self.convert_pixmap_to_pil_image = kwargs.pop('convert_pixmap_to_pil_image')
        self.img = kwargs.pop('img')
        self.top = kwargs.pop('top')
        self.left = kwargs.pop('left')
        self.bottom = kwargs.pop('bottom')
        self.right = kwargs.pop('right')
        self.layer = kwargs.pop("layer")
        super().__init__(*args)

    def run(self):
        self.convert_pixmap_to_pil_image(
            self.img,
            self.top,
            self.left,
            self.bottom,
            self.right,
            self.layer
        )
        self.finished.emit()


class RasterizationTask(QRunnable):
    def __init__(self, worker):
        super().__init__()
        self.worker = worker

    def run(self):
        self.worker.run()


class CanvasBrushesMixin:
    thread = None
    worker = None

    @property
    def left_line_extremity(self):
        return self.current_layer.left_line_extremity

    @left_line_extremity.setter
    def left_line_extremity(self, value):
        self.current_layer.left_line_extremity = value

    @property
    def right_line_extremity(self):
        return self.current_layer.right_line_extremity

    @right_line_extremity.setter
    def right_line_extremity(self, value):
        self.current_layer.right_line_extremity = value

    @property
    def top_line_extremity(self):
        return self.current_layer.top_line_extremity

    @top_line_extremity.setter
    def top_line_extremity(self, value):
        self.current_layer.top_line_extremity = value

    @property
    def bottom_line_extremity(self):
        return self.current_layer.bottom_line_extremity

    @bottom_line_extremity.setter
    def bottom_line_extremity(self, value):
        self.current_layer.bottom_line_extremity = value

    @property
    def last_left(self):
        return self.current_layer.last_left

    @last_left.setter
    def last_left(self, value):
        self.current_layer.last_left = value

    @property
    def last_top(self):
        return self.current_layer.last_top

    @last_top.setter
    def last_top(self, value):
        self.current_layer.last_top = value

    @property
    def min_x(self):
        return self.current_layer.min_x

    @min_x.setter
    def min_x(self, value):
        self.current_layer.min_x = value

    @property
    def min_y(self):
        return self.current_layer.min_y

    @min_y.setter
    def min_y(self, value):
        self.current_layer.min_y = value

    @property
    def last_pos(self):
        return self.current_layer.last_pos

    @last_pos.setter
    def last_pos(self, value):
        self.current_layer.last_pos = value

    @property
    def color(self):
        return self.current_layer.color

    @color.setter
    def color(self, value):
        self.current_layer.color = value

    @property
    def line_width(self):
        return self.current_layer.line_width

    @line_width.setter
    def line_width(self, value):
        self.current_layer.line_width = value

    @property
    def opacity(self):
        return self.current_layer.opacity

    def initialize(self):
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)

    def draw(self, layer, index):
        path = QPainterPath()
        painter = None
        for line in layer.lines:
            pen = line.pen
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            # set opacity based on current_layer opacity
            if self.line_width is None or self.line_width != line.width:
                self.line_width = line.width
                self.draw_path(path, painter)
                painter = None
            if self.color is None or self.color != line.color:
                self.color = line.color
                self.draw_path(path, painter)
                painter = None
            if not painter:
                painter = QPainter(self.canvas_container)
                painter.setBrush(self.brush)
                painter.setOpacity(1.0)
                path = QPainterPath()
            painter.setPen(pen)

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
        if len(self.current_layer.lines) > 0:
            self.rasterize_lines(final=True)
        brush_size = int(self.settings_manager.settings.mask_brush_size.get() / 2)
        image = self.current_layer.image_data.image if self.current_layer.image_data.image is not None else None
        image_pos = self.current_layer.image_data.position if self.current_layer.image_data.image is not None else None
        if image is None:
            return
        start = event.pos() - QPoint(self.pos_x, self.pos_y) - image_pos
        if image:
            image = image.copy()
            draw = ImageDraw.Draw(image)
            if self.last_pos is None:
                self.last_pos = start
            draw.line([
                self.last_pos.x(),
                self.last_pos.y(),
                start.x(),
                start.y()
            ], fill=(0, 0, 0, 0), width=brush_size*2, joint="curve")
            draw.ellipse((
                start.x() - brush_size,
                start.y() - brush_size,
                start.x() + brush_size,
                start.y() + brush_size
            ), fill=(0, 0, 0, 0))
            self.current_layer.image_data.image = image
            self.last_pos = start
            self.update()
        self.update()

    def pen(self, event):
        brush_color = "#ffffff"
        if event.button() == Qt.MouseButton.LeftButton or Qt.MouseButton.LeftButton in event.buttons():
            brush_color = self.settings_manager.settings.primary_color.get()
        brush_color = QColor(brush_color)
        pen = QPen(
            brush_color,
            self.settings_manager.settings.mask_brush_size.get()
        )
        return pen

    def handle_draw(self, event):
        start = event.pos() - QPoint(self.pos_x, self.pos_y)
        pen = self.pen(event)
        if len(self.current_layer.lines) > 0:
            previous = LineData(self.current_layer.lines[-1].start_point, start, pen, self.current_layer_index)
            self.current_layer.lines[-1] = previous

        end = event.pos() - QPoint(self.pos_x + 1, self.pos_y)
        line_data = LineData(start, end, pen, self.current_layer_index)
        self.current_layer.lines.append(line_data)
        self.update()

    def get_line_extremities(self, lines):
        for line in lines:
            start_x = line.start_point.x()
            start_y = line.start_point.y()
            end_x = line.end_point.x()
            end_y = line.end_point.y()

            brush_size = int(self.settings_manager.settings.mask_brush_size.get() / 2)
            min_x = min(start_x, end_x) - brush_size
            min_y = min(start_y, end_y) - brush_size
            max_x = max(start_x, end_x) + brush_size
            max_y = max(start_y, end_y) + brush_size
            if self.left_line_extremity is None:
                self.left_line_extremity = min_x
            else:
                self.left_line_extremity = min(self.left_line_extremity, min_x)
            if self.right_line_extremity is None:
                self.right_line_extremity = max_x
            else:
                self.right_line_extremity = max(self.right_line_extremity, max_x)
            if self.top_line_extremity is None:
                self.top_line_extremity = min_y
            else:
                self.top_line_extremity = min(self.top_line_extremity, min_y)
            if self.bottom_line_extremity is None:
                self.bottom_line_extremity = max_y
            else:
                self.bottom_line_extremity = max(self.bottom_line_extremity, max_y)
        return self.top_line_extremity, self.left_line_extremity, self.bottom_line_extremity, self.right_line_extremity

    def rasterize_lines(self, final=False):
        max_lines = len(self.current_layer.lines)
        if max_lines == 0:
            return

        lines = self.current_layer.lines[:max_lines]
        top, left, bottom, right = self.get_line_extremities(lines)
        brush_size = self.settings_manager.settings.mask_brush_size.get()
        if brush_size > 1:
            brush_size = int(brush_size / 2)

        # create a QImage with the size of the lines
        min_x = min(left, right) - brush_size
        max_x = max(left, right) - brush_size
        min_y = min(top, bottom) - brush_size
        max_y = max(top, bottom) - brush_size
        width = abs(max_x - min_x)
        height = abs(max_y - min_y)
        img = QImage(QSize(width, height), QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        painter.setBrush(self.brush)
        painter.setOpacity(1.0)
        path = self.create_image_path(painter, lines)
        painter.drawPath(path)
        painter.end()

        worker = RasterizationWorker(
            convert_pixmap_to_pil_image=self.convert_pixmap_to_pil_image,
            img=img,
            top=top,
            left=left,
            bottom=bottom,
            right=right,
            layer=self.current_layer
        )
        task = RasterizationTask(worker)
        self.thread_pool.start(task)
        # task.setAutoDelete(True)
        task.worker.finished.connect(lambda _max_lines=max_lines, _final=final: self.finalize_pixmap(_max_lines, _final))

    def finalize_pixmap(self, max_lines, final=False):
        self.current_layer.lines = self.current_layer.lines[max_lines:]
        self.update()

    def create_image_path(self, painter, lines):
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.WindingFill)
        for line in lines:
            pen = line.pen
            color = line.color
            pen.setColor(color)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

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

    def convert_pixmap_to_pil_image(
        self,
        img: Image,
        top: int,
        left: int,
        bottom: int,
        right: int,
        layer: LayerData
    ):
        try:
            img = Image.fromqpixmap(img)
        except UnidentifiedImageError:
            return None
        self.insert_rasterized_line_image(
            QRect(left, top, right, bottom),
            img,
            layer
        )
