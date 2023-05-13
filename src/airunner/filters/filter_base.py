import os
from PyQt6 import uic


class FilterBase:
    ui_name = ""
    window_title = ""

    @property
    def filter(self):
        return None

    def update_canvas(self):
        self.canvas.update()

    def __init__(self, parent):
        self.filter_window = None
        self.parent = parent
        self.canvas = parent.canvas

    def show(self):
        self.filter_window = uic.loadUi(os.path.join(f"pyqt/{self.ui_name}.ui"))
        self.filter_window.setWindowTitle(self.window_title)

    def cancel_filter(self):
        self.filter_window.close()
        self.parent.current_filter = None
        self.update_canvas()

    def apply_filter(self):
        self.canvas.apply_filter()
        self.filter_window.close()
        self.update_canvas()
