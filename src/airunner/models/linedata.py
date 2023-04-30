from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QPen


class LineData:
    @property
    def pen(self):
        pen = self._pen if self._pen else {
            "color": "#000000",
            "width": 1,
            "style": Qt.PenStyle.SolidLine,
            "opacity": 255
        }
        return QPen(
            QColor(pen["color"]),
            pen["width"],
            pen["style"]
        )

    @property
    def opacity(self):
        return self._pen["opacity"] if self._pen else 255

    def __init__(self, start_point: QPoint, end_point: QPoint, pen: QPen, layer_index: int, opacity: int):
        self.start_point = start_point
        self.end_point = end_point
        # do not store as a qpen, store as a dict
        self._pen = {
            "color": pen.color(),
            "width": pen.width(),
            "style": pen.style(),
            "opacity": opacity
        }
        self.layer_index = layer_index

    def intersects(self, start: QPoint, brush_size: int):
        # check x and use brush size
        if self.start_point.x() > start.x() - brush_size and self.start_point.x() < start.x() + brush_size:
            if self.start_point.y() > start.y() - brush_size and self.start_point.y() < start.y() + brush_size:
                return True
        return False
