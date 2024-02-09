from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt6.QtGui import QPainterPath, QMouseEvent
from PyQt6.QtCore import Qt


class CustomGraphicsView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._startPos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            path = QPainterPath()
            path.addRect(self._startPos.x(), self._startPos.y(), event.pos().x() - self._startPos.x(), event.pos().y() - self._startPos.y())
            self.scene().setSelectionArea(path, Qt.ItemSelectionMode.IntersectsItemShape)
        super().mouseReleaseEvent(event)
