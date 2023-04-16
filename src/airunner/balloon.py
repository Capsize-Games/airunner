from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QPainterPath, QPainter, QPen, QColor, QPolygonF
from PyQt6.QtWidgets import QWidget


class Balloon(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tail_pos = QPointF(0, 0)
        self._balloon_path = QPainterPath()
        self._tail_path = QPainterPath()
        self._color = QColor(255, 255, 255)
        self._pen = QPen(QColor(0, 0, 0), 3)
        self._update_balloon_path()

    def draw(self, painter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self._pen)
        painter.setBrush(self._color)
        painter.drawPath(self._balloon_path)
        painter.drawPath(self._tail_path)

    def resizeEvent(self, event):
        self._update_balloon_path()

    def set_color(self, color):
        self._color = color
        self.update()

    def set_pen(self, pen):
        self._pen = pen
        self.update()

    def set_tail_pos(self, pos):
        self._tail_pos = pos
        self._update_balloon_path()
        self.update()

    def _update_balloon_path(self):
        balloon_rect = QRectF(0, 0, self.width(), self.height() - 20)
        tail_rect = QRectF(0, 0, 20, 20)
        tail_rect.moveCenter(self._tail_pos)

        self._balloon_path = QPainterPath()
        self._balloon_path.addRoundedRect(balloon_rect, 10, 10)

        self._tail_path = QPainterPath()
        tail_points = QPolygonF()
        tail_points.append(QPointF(tail_rect.left(), tail_rect.center().y()))
        tail_points.append(QPointF(tail_rect.right(), tail_rect.top()))
        tail_points.append(QPointF(tail_rect.right(), tail_rect.bottom()))
        self._tail_path.addPolygon(tail_points)
        self._tail_path.closeSubpath()

        self.update()
