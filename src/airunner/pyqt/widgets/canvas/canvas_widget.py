from PyQt6.QtCore import QRect, QPoint
from PyQt6.QtWidgets import QFrame, QLabel, QGridLayout

from airunner.pyqt.widgets.base_widget import BaseWidget
from airunner.pyqt.widgets.canvas.canvas import Ui_canvas


class CanvasWidget(BaseWidget):
    widget_class_ = Ui_canvas

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.initialize_debugging()
