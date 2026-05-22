from PySide6.QtCore import QRectF, QLineF
from PySide6.QtGui import QColor, QPen, QPainter
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import QPointF

from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.components.art.utils.canvas_position_manager import (
    CanvasPositionManager,
    ViewState,
)


class GridGraphicsItem(SettingsMixin, QGraphicsItem):
    def __init__(self, view, center_point: QPointF):
        super().__init__()
        del center_point
        self.view = view
        self.setZValue(-100)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
        # Note: We read center_pos directly from view.center_pos in paint()
        # to ensure we always have the current value

    def _document_rect(self) -> QRectF:
        if not hasattr(self.view, "document_rect"):
            return QRectF()
        try:
            rect = self.view.document_rect()
        except Exception:
            return QRectF()
        return QRectF(rect) if rect is not None else QRectF()

    def _view_state(self) -> ViewState:
        canvas_offset = getattr(self.view, "canvas_offset", QPointF(0.0, 0.0))
        grid_compensation = getattr(
            self.view,
            "grid_compensation_offset",
            getattr(self.view, "_grid_compensation_offset", QPointF(0.0, 0.0)),
        )
        return ViewState(
            canvas_offset=QPointF(canvas_offset),
            grid_compensation=QPointF(grid_compensation),
        )

    def _display_document_rect(self) -> QRectF:
        document_rect = self._document_rect()
        if document_rect.isEmpty():
            return QRectF()
        display_origin = CanvasPositionManager.absolute_to_display(
            document_rect.topLeft(),
            self._view_state(),
        )
        return QRectF(
            display_origin.x(),
            display_origin.y(),
            document_rect.width(),
            document_rect.height(),
        )

    def _grid_origin(self) -> QPointF:
        center_pos = getattr(self.view, "center_pos", None)
        if center_pos is not None:
            return QPointF(center_pos)

        document_rect = self._document_rect()
        if not document_rect.isEmpty():
            return QPointF(document_rect.topLeft())
        return QPointF(0.0, 0.0)

    def _display_grid_origin(self) -> QPointF:
        return CanvasPositionManager.absolute_to_display(
            self._grid_origin(),
            self._view_state(),
        )

    def boundingRect(self) -> QRectF:
        document_rect = self._display_document_rect()
        if not document_rect.isEmpty():
            return document_rect
        return self.view.mapToScene(self.view.viewport().rect()).boundingRect()

    def paint(self, painter: QPainter, option, widget=None):
        cell_size = self.view.grid_settings.cell_size
        if cell_size <= 0:
            return
        color = QColor(self.view.grid_settings.line_color)
        pen = QPen(color, self.view.grid_settings.line_width)
        painter.setPen(pen)
        visible_rect = self.view.mapToScene(
            self.view.viewport().rect()
        ).boundingRect()
        document_rect = self._display_document_rect()
        if not document_rect.isEmpty():
            visible_rect = visible_rect.intersected(document_rect)
            if visible_rect.isEmpty():
                return

        left = visible_rect.left()
        right = visible_rect.right()
        top = visible_rect.top()
        bottom = visible_rect.bottom()

        grid_origin = self._display_grid_origin()
        grid_base_x = grid_origin.x()
        grid_base_y = grid_origin.y()
        
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
            painter.drawLine(QLineF(x, top, x, bottom))
            x += cell_size
        # Draw horizontal lines
        y = start_y
        while y <= bottom:
            painter.drawLine(QLineF(left, y, right, y))
            y += cell_size
