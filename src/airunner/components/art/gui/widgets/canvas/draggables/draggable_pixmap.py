from typing import Optional
from PySide6.QtCore import QPoint, QRectF
from PySide6.QtGui import QPainter, QImage
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from airunner.enums import CanvasToolName
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.application import snap_to_grid
from airunner.components.application.gui.windows.main.settings_mixin import (
    SettingsMixin,
)
from airunner.utils.settings import get_qsettings
from airunner.components.art.data.drawingpad_settings import DrawingPadSettings


class DraggablePixmap(
    MediatorMixin,
    SettingsMixin,
    QGraphicsItem,
):
    def __init__(
        self,
        qimage: Optional[QImage] = None,
        *,
        layer_id: Optional[int] = None,
        use_layer_context: bool = True,
    ):
        self._layer_id_override: Optional[int] = layer_id
        self._use_layer_context = use_layer_context
        super().__init__()
        self._qimage = qimage
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.last_pos = QPoint(0, 0)
        self.save = False
        if self._use_layer_context:
            settings = self.drawing_pad_settings
            pos = settings.pos if settings is not None else (0, 0)
        else:
            pos = (0, 0)
        self.settings = get_qsettings()
        # Threshold for snapping (percentage of cell size)
        self.snap_threshold = 0.5
        self.setPos(QPoint(pos[0], pos[1]))

    @property
    def canvas_offset_x(self) -> float:
        return self.settings.value("canvas_offset_x", 0, type=float)

    @property
    def canvas_offset_y(self) -> float:
        return self.settings.value("canvas_offset_y", 0, type=float)

    @property
    def current_tool(self):
        val = self.application_settings.current_tool
        try:
            return CanvasToolName(val) if val is not None else None
        except ValueError:
            return None

    def _resolve_layer_id(self) -> Optional[int]:
        if not self._use_layer_context:
            return None
        if self._layer_id_override is not None:
            return self._layer_id_override
        return self._get_current_selected_layer_id()

    def set_layer_context(self, layer_id: Optional[int]) -> None:
        if not self._use_layer_context:
            self._layer_id_override = None
            return
        self._layer_id_override = layer_id

    @property
    def drawing_pad_settings(self) -> DrawingPadSettings:  # type: ignore[override]
        layer_id = self._resolve_layer_id()
        if layer_id is not None:
            return self._get_layer_specific_settings(
                DrawingPadSettings, layer_id=layer_id
            )
        return super().drawing_pad_settings

    def boundingRect(self) -> QRectF:
        if self._qimage is not None:
            return QRectF(self._qimage.rect())
        return QRectF()

    def updateImage(self, qimage: QImage):
        """Update the image data directly without conversion to pixmap"""
        self.prepareGeometryChange()
        self._qimage = qimage
        self.update()  # Schedule a repaint of this item

    @property
    def qimage(self) -> Optional[QImage]:
        """Return the underlying QImage reference if available."""
        return self._qimage

    def set_qimage(self, qimage: QImage) -> None:
        """Replace the underlying QImage reference and refresh the item."""
        self._qimage = qimage
        self.update()

    def mouseMoveEvent(self, event):
        if self.current_tool not in [
            CanvasToolName.MOVE,
        ]:
            return
        super().mouseMoveEvent(event)
        self.snap_to_grid_when_close()

    def mouseReleaseEvent(self, event):
        if self.current_tool in [
            CanvasToolName.MOVE,
        ]:
            # Pass the current position for saving instead of None values
            current_x = int(self.x())
            current_y = int(self.y())
            self.update_position(x=current_x, y=current_y, save=True)
        super().mouseReleaseEvent(event)

    def snap_to_grid_when_close(self, x=None, y=None):
        """Only snap to grid when close enough to grid lines"""
        if x is None:
            x = int(self.x())
        if y is None:
            y = int(self.y())

        # Get the absolute coordinates (including canvas offset)
        abs_x = x + self.canvas_offset_x
        abs_y = y + self.canvas_offset_y

        if self.grid_settings.snap_to_grid:
            cell_size = self.grid_settings.cell_size

            if cell_size <= 0:  # Safety check
                return

            # Calculate threshold distance in pixels
            threshold_dist = cell_size * self.snap_threshold

            # Calculate distance to nearest grid line in x and y directions
            x_mod = abs_x % cell_size
            y_mod = abs_y % cell_size

            # Get distance to closest grid line
            x_dist = min(x_mod, cell_size - x_mod)
            y_dist = min(y_mod, cell_size - y_mod)

            # Determine if we should snap in each direction
            snap_x = x_dist <= threshold_dist
            snap_y = y_dist <= threshold_dist

            # Only snap the axes that are close to grid lines
            if snap_x or snap_y:
                # Get the potential snapped position
                snapped_x, snapped_y = snap_to_grid(
                    self.grid_settings,
                    abs_x,
                    abs_y,
                    False,  # Use rounding for better visual centering
                )

                # Only apply snapping to the axes that should be snapped
                if snap_x:
                    x = snapped_x - self.canvas_offset_x
                if snap_y:
                    y = snapped_y - self.canvas_offset_y

        self.update_position(x, y, False)  # Don't save during dragging

    def update_position(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        save: bool = True,
    ):
        if x is not None and y is not None:
            self.setPos(QPoint(x, y))

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ):
        if self._qimage is not None:
            painter.drawImage(0, 0, self._qimage)
