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
        # Note: We read center_pos directly from view.center_pos in paint()
        # to ensure we always have the current value

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

        left = int(visible_rect.left())
        right = int(visible_rect.right())
        top = int(visible_rect.top())
        bottom = int(visible_rect.bottom())

        # Get the current center_pos from the view (where items are placed).
        # Grid lines should pass through center_pos and every cell_size interval.
        # 
        # To find where grid lines should be drawn in screen coordinates:
        # 1. A grid line exists at absolute positions: center_x, center_x ± cell_size, center_x ± 2*cell_size, etc.
        # 2. To convert absolute to display: display = absolute - offset
        # 3. So grid lines are at display positions: (center_x - offset) + n*cell_size
        #
        # We need to find the first grid line position >= left:
        # start_x = center_x - offset_x + n*cell_size >= left
        # n >= (left - center_x + offset_x) / cell_size
        # n = ceil((left - center_x + offset_x) / cell_size)
        # start_x = center_x - offset_x + n * cell_size
        
        try:
            center_pos = getattr(self.view, 'center_pos', None)
            center_x = int(center_pos.x()) if center_pos is not None else 0
            center_y = int(center_pos.y()) if center_pos is not None else 0
        except Exception:
            center_x = 0
            center_y = 0

        # Calculate grid line base position in display coordinates
        # Grid lines pass through (center - offset) in display space
        grid_base_x = center_x - int(offset_x)
        grid_base_y = center_y - int(offset_y)
        
        # Find the first grid line position at or before the left/top edge
        # We want: grid_base_x + n*cell_size <= left, with n being the largest such integer
        # n = floor((left - grid_base_x) / cell_size)
        import math
        n_x = math.floor((left - grid_base_x) / cell_size)
        n_y = math.floor((top - grid_base_y) / cell_size)
        
        start_x = grid_base_x + n_x * cell_size
        start_y = grid_base_y + n_y * cell_size

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
