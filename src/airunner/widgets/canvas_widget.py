from PyQt6.QtCore import QRect, QPoint
from PyQt6.QtWidgets import QFrame, QLabel, QGridLayout

from airunner.widgets.base_widget import BaseWidget


class CanvasWidget(BaseWidget):
    name = "canvas"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.initialize_debugging()
