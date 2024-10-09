from airunner.enums import SignalCode
from airunner.utils.random_seed import random_seed
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.seed.templates.seed_ui import Ui_seed_widget


class SeedWidget(BaseWidget):
    widget_class_ = Ui_seed_widget
    name = "seed_widget"

    def __init__(self, *args, **kwargs):
        self.icons = [
            ("dice-game-icon", "random_button")
        ]
        super().__init__(*args, **kwargs)
        self.register(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, self.on_application_settings_changed_signal)
        self.ui.lineEdit.blockSignals(True)
        self.ui.lineEdit.setText(str(self.generator_settings.seed))
        self.ui.lineEdit.setEnabled(not self.generator_settings.random_seed)
        self.ui.random_button.setChecked(self.generator_settings.random_seed)
        self.ui.lineEdit.blockSignals(False)

    def on_application_settings_changed_signal(self):
        try:
            self.ui.lineEdit.blockSignals(True)
            self.ui.lineEdit.setText(str(self.generator_settings.seed))
            self.ui.lineEdit.blockSignals(False)
        except RuntimeError as e:
            pass

    def action_clicked_button_random_seed(self, value):
        self.update_generator_settings("random_seed", value)
        self.ui.lineEdit.setEnabled(not value)
        if value is True:
            seed = random_seed()
            self.update_generator_settings("seed", seed)
            self.ui.lineEdit.setText(str(seed))

    def action_value_changed_seed(self, value):
        self.update_generator_settings("seed", int(value))
