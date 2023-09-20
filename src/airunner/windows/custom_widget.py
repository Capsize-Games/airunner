import os
from PyQt6 import uic
from PyQt6.QtWidgets import QWidget


class CustomWidget(QWidget):
    def __init__(self, *args, **kwargs):
        app = kwargs.pop("app")
        filename = kwargs.pop("filename", None)
        settings_manager = kwargs.pop("settings_manager")
        super().__init__(*args, **kwargs)
        self.app = app
        self.settings_manager = settings_manager
        if filename:
            uic.loadUi(os.path.join(f"pyqt/widgets/{filename}.ui"), self)
