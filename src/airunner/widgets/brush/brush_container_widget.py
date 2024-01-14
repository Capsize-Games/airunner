from contextlib import contextmanager
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.brush.templates.brush_widget_ui import Ui_brush_widget
from airunner.data.session_scope import session_scope


class BrushContainerWidget(BaseWidget):
    widget_class_ = Ui_brush_widget
    _brush = None

    @contextmanager
    def brush(self):
        with session_scope() as session:
            session.add(self._brush)
            yield self._brush

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.brush_size_slider.setProperty("current_value", self.app.settings["brush_settings"]["size"])
        self.ui.brush_size_slider.initialize()
