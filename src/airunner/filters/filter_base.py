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
        # on escape, call the "cancel" button on the QDialogButtonBox
        self.filter_window.keyPressEvent = lambda event: self.cancel_filter() if event.key() == 16777216 else None

    def cancel_filter(self):
        self.filter_window.close()
        self.parent.canvas.cancel_filter()
        self.update_canvas()

    def apply_filter(self):
        self.parent.canvas.apply_filter(self.filter)
        self.filter_window.close()
        self.update_canvas()

    def preview_filter(self):
        self.parent.canvas.preview_filter(self.filter)
        self.update_canvas()
