from contextlib import contextmanager
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.brush.templates.brush_widget_ui import Ui_brush_widget


class BrushContainerWidget(BaseWidget):
    widget_class_ = Ui_brush_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.brush_size_slider.setProperty("current_value", self.brush_settings["size"])
        self.ui.brush_size_slider.initialize()
