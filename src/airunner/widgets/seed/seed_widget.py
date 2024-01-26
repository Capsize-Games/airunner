from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.seed.templates.seed_ui import Ui_seed_widget


class SeedWidget(BaseWidget):
    seed = 42
    widget_class_ = Ui_seed_widget
    name = "seed_widget"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal)

    def on_application_settings_changed_signal(self):
        self.ui.lineEdit.setText(str(self.seed))

    def action_clicked_button_random_seed(self, value):
        settings = self.settings
        settings["generator_settings"]["random_seed"] = value
        self.settings = settings
        self.ui.lineEdit.setEnabled(not value)

    def action_value_changed_seed(self, value):
        self.seed = value
