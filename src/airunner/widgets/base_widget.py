import os
from PyQt6 import QtGui
from PyQt6 import uic
from PyQt6.QtWidgets import QWidget
from airunner.widgets.slider_widget import SliderWidget


class BaseWidget(QWidget):
    name = None
    icons = {}

    @property
    def is_dark(self):
        return self.settings_manager.settings.dark_mode_enabled.get()

    @property
    def settings(self):
        return self.app.settings

    @property
    def settings_manager(self):
        return self.app.settings_manager

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
            spinbox_maximum=spinbox_maximum
        )

    def add_to_grid(self, widget, row, column, row_span=1, column_span=1):
        self.layout().addWidget(widget, row, column, row_span, column_span)

    def __init__(self, *args, **kwargs):
        self.app = kwargs.pop("app", None)
        super().__init__(*args, **kwargs)
        if self.name:
            uic.loadUi(f"pyqt/widgets/{self.name}.ui", self)

    def set_stylesheet(self):
        for button, icon in self.icons.items():
            getattr(self, button).setIcon(
                QtGui.QIcon(
                    os.path.join(f"src/icons/{icon}{'-light' if self.is_dark else ''}.png")
                )
            )