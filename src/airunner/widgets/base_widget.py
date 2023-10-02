import os
from PyQt6 import QtGui
from PyQt6.QtWidgets import QWidget

from airunner.aihandler.settings_manager import SettingsManager
from airunner.utils import get_main_window


class BaseWidget(QWidget):
    widget_class_ = None
    icons = {}
    ui = None
    qss_filename = None

    @property
    def is_dark(self):
        return self.settings_manager.dark_mode_enabled

    @property
    def canvas(self):
        return self.app.canvas

    def add_to_grid(self, widget, row, column, row_span=1, column_span=1):
        self.layout().addWidget(widget, row, column, row_span, column_span)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = get_main_window()
        self.settings_manager = SettingsManager()
        self.ui = self.widget_class_()
        self.ui.setupUi(self)
        if self.qss_filename:
            theme_name = "dark_theme"
            here = os.path.dirname(os.path.realpath(__file__))
            with open(os.path.join(here, "..", "styles", theme_name, self.qss_filename), "r") as f:
                stylesheet = f.read()
            self.setStyleSheet(stylesheet)

    def set_stylesheet(self, is_dark=None, button_name=None, icon=None):
        is_dark = self.is_dark if is_dark is None else is_dark
        if button_name is None or icon is None:
            for button_name, icon in self.icons.items():
                self.set_button_icon(is_dark, button_name, icon)
        else:
            self.set_button_icon(is_dark, button_name, icon)

    def set_button_icon(self, is_dark, button_name, icon):
        try:
            getattr(self, button_name).setIcon(
                QtGui.QIcon(
                    os.path.join(f"src/icons/{icon}{'-light' if is_dark else ''}.png")
                )
            )
        except AttributeError as e:
            pass
