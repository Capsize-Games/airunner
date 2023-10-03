from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.canvas.templates.canvas_ui import Ui_canvas


class CanvasWidget(BaseWidget):
    widget_class_ = Ui_canvas

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.initialize_debugging()
