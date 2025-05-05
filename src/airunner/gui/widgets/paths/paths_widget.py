from airunner.enums import SignalCode
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.paths.templates.paths_ui import Ui_paths_form


class PathsWidget(BaseWidget):
    widget_class_ = Ui_paths_form

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def action_button_clicked_reset(self):
        self.api.reset_paths()
