import os
from PyQt6 import QtGui
from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QApplication, QMainWindow

from airunner.aihandler.settings_manager import SettingsManager
from airunner.pyqt.widgets.slider.slider_widget import SliderWidget
from airunner.utils import get_main_window


class BaseWidget(QWidget):
    widget_class_ = None
    icons = {}
    ui = None

    @property
    def is_dark(self):
        return self.settings_manager.dark_mode_enabled

    @property
    def canvas(self):
        return self.app.canvas

    def create_slider_widget(
        self,
        label_text,
        slider_callback,
        slider_minimum=1,
        slider_maximum=100,
        slider_tick_interval=1,
        slider_single_step=1,
        slider_page_step=1,
        spinbox_single_step=0.01,
        spinbox_page_step=0.01,
        spinbox_minimum=0,
        spinbox_maximum=100,
        display_as_float=False
    ):
        return SliderWidget(
            label_text=label_text,
            slider_callback=slider_callback,
            slider_minimum=slider_minimum,
            slider_maximum=slider_maximum,
            slider_tick_interval=slider_tick_interval,
            slider_single_step=slider_single_step,
            slider_page_step=slider_page_step,
            spinbox_single_step=spinbox_single_step,
            spinbox_page_step=spinbox_page_step,
            spinbox_minimum=spinbox_minimum,
            spinbox_maximum=spinbox_maximum,
            display_as_float=display_as_float
        )

    def add_to_grid(self, widget, row, column, row_span=1, column_span=1):
        self.layout().addWidget(widget, row, column, row_span, column_span)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = get_main_window()
        self.settings_manager = SettingsManager()
        self.ui = self.widget_class_()
        self.ui.setupUi(self)

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
