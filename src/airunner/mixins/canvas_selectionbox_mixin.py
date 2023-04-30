from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QPainter, QPen


class CanvasSelectionboxMixin:
    def draw_selection_box(self, painter):
        if self.select_start is not None and self.select_end is not None:
            # the rectangle should have a dashed line border
            painter.setPen(QPen(Qt.GlobalColor.red, 1))
            painter.setBrush(Qt.GlobalColor.transparent)
            painter.drawRect(QRect(self.select_start, self.select_end))

    def paint_event(self, event):
        painter = QPainter(self.canvas_container)
        self.draw_selection_box(painter)
        painter.end()
