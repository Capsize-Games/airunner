from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPen, QPainter
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import QPointF

from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)


class GridGraphicsItem(SettingsMixin, QGraphicsItem):
    def __init__(self, view, center_point: QPointF):
        super().__init__()
        self.view = view
        self.setZValue(-100)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
        self._paint_count = 0
        self.center_point = center_point

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

        # Combine canvas offset (user pan) with grid compensation (viewport adjustments)
        offset_x = (
            self.view.canvas_offset.x()
            - self.view.grid_compensation_offset.x()
        )
        offset_y = (
            self.view.canvas_offset.y()
            - self.view.grid_compensation_offset.y()
        )

        # Log grid offset calculation only on first few paints to avoid spam
        if self._paint_count < 3:
            self._paint_count += 1

        left = int(visible_rect.left())
        right = int(visible_rect.right())
        top = int(visible_rect.top())
        bottom = int(visible_rect.bottom())

        # Incorporate the provided center_point so the grid lines align with
        # the same absolute origin used for placing items. The center_point
        # is an absolute-position anchor (from the view) and must be included
        # when calculating the modular grid start positions.
        try:
            center_x = (
                int(self.center_point.x())
                if self.center_point is not None
                else 0
            )
            center_y = (
                int(self.center_point.y())
                if self.center_point is not None
                else 0
            )
        except Exception:
            center_x = 0
            center_y = 0

        # Compute starts using (screen_coord + offset - center) modulo cell_size
        # so that the visual grid aligns with absolute coordinates anchored at center_point.
        start_x = left - ((left + int(offset_x) - center_x) % cell_size)
        start_y = top - ((top + int(offset_y) - center_y) % cell_size)

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
