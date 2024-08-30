from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.paths.templates.paths_ui import Ui_paths_form


class PathsWidget(BaseWidget):
    widget_class_ = Ui_paths_form

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def action_button_clicked_reset(self):
        self.emit_signal(SignalCode.APPLICATION_RESET_PATHS_SIGNAL)
