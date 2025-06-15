from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPen, QPainter
from PySide6.QtWidgets import QGraphicsItem


class GridGraphicsItem(QGraphicsItem):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.setZValue(-100)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)

    def boundingRect(self) -> QRectF:
        # Always cover the visible area
        rect = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
        return rect

    def paint(self, painter: QPainter, option, widget=None):
        cell_size = self.view.grid_settings.cell_size
        if cell_size <= 0:
            return
        color = QColor(self.view.grid_settings.line_color)
        pen = QPen(color, self.view.grid_settings.line_width)
        painter.setPen(pen)
        visible_rect = self.boundingRect()
        offset_x = self.view.canvas_offset.x()
        offset_y = self.view.canvas_offset.y()
        left = int(visible_rect.left())
        right = int(visible_rect.right())
        top = int(visible_rect.top())
        bottom = int(visible_rect.bottom())
        start_x = left - ((left + int(offset_x)) % cell_size)
        start_y = top - ((top + int(offset_y)) % cell_size)
        # Draw vertical lines
        x = start_x
        while x <= right:
            painter.drawLine(x, top, x, bottom)
            x += cell_size
        # Draw horizontal lines
        y = start_y
        while y <= bottom:
            painter.drawLine(left, y, right, y)
            y += cell_size
