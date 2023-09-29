from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.paths.path_widget import PathWidget
from airunner.widgets.paths.templates.paths_ui import Ui_paths_form


class PathsWidget(BaseWidget):
    widget_class_ = Ui_paths_form

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.initialize_widgets()

    def action_button_clicked_reset(self):
        self.settings_manager.path_settings.reset_paths()
        self.initialize_widgets()

    def initialize_widgets(self):
        widgets = self.findChildren(PathWidget)
        for widget in widgets:
            widget.initialize()
