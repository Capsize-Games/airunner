from PyQt6.QtGui import QPainter


class CanvasWidgetsMixin:
    def draw(self, layer, index):
        painter = QPainter(self.canvas_container)
        self.draw_widgets(layer, index, painter)
        painter.end()

    def draw_widgets(self, layer, index, painter):
        for widget in layer.widgets:
            widget.draw(painter)
