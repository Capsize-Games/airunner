from typing import Optional
from PySide6.QtWidgets import QGraphicsItem
from airunner.gui.widgets.canvas.draggables.draggable_pixmap import (
    DraggablePixmap,
)


class LayerImageItem(DraggablePixmap):
    def __init__(self, pixmap, layer_image_data):
        self.layer_image_data = layer_image_data
        super().__init__(pixmap)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

    def update_position(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        save: bool = True,
    ):
        super().update_position(x, y, save)

        if save:
            self.update_drawing_pad_settings("x_pos", x)
            self.update_drawing_pad_settings("y_pos", y)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        pos = self.pos()
        self.layer_image_data["pos_x"] = pos.x()
        self.layer_image_data["pos_y"] = pos.y()
