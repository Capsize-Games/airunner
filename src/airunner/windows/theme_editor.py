from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from airunner.windows.base_window import BaseWindow


class ThemeEditor(BaseWindow):
    template_name = "theme_editor"
    window_title = "Theme Editor"

    def initialize_window(self):
        pass