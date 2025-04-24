from airunner.enums import SignalCode
from airunner.utils.application import random_seed
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.seed.templates.seed_ui import Ui_seed_widget


class SeedWidget(BaseWidget):
    widget_class_ = Ui_seed_widget
    name = "seed_widget"

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal
        }
        self.icons = [("dice-game-icon", "random_button")]
        super().__init__(*args, **kwargs)
        self.ui.lineEdit.blockSignals(True)

        # Set default value for seed if None
        seed = (
            self.generator_settings.seed
            if self.generator_settings.seed is not None
            else random_seed()
        )
        self.ui.lineEdit.setText(str(seed))

        # Set default value for random_seed if None
        random_seed_value = (
            bool(self.generator_settings.random_seed)
            if self.generator_settings.random_seed is not None
            else False
        )

        self.ui.lineEdit.setEnabled(not random_seed_value)
        self.ui.random_button.setChecked(random_seed_value)
        self.ui.lineEdit.blockSignals(False)

        # Make sure the settings are updated with the default values if they were None
        if self.generator_settings.seed is None:
            self.update_generator_settings("seed", seed)
        if self.generator_settings.random_seed is None:
            self.update_generator_settings("random_seed", random_seed_value)

    def on_application_settings_changed_signal(self):
        try:
            self.ui.lineEdit.blockSignals(True)
            seed = (
                self.generator_settings.seed
                if self.generator_settings.seed is not None
                else random_seed()
            )
            self.ui.lineEdit.setText(str(seed))
            self.ui.lineEdit.blockSignals(False)
        except RuntimeError as _e:
            pass

    def action_clicked_button_random_seed(self, value):
        self.update_generator_settings("random_seed", value)
        self.ui.lineEdit.setEnabled(not value)
        if value is True:
            seed = random_seed()
            self.update_generator_settings("seed", seed)
            self.ui.lineEdit.setText(str(seed))

    def action_value_changed_seed(self, value):
        try:
            seed_value = int(value)
            self.update_generator_settings("seed", seed_value)
        except ValueError:
            # If conversion fails, set a random seed
            seed = random_seed()
            self.update_generator_settings("seed", seed)
            self.ui.lineEdit.setText(str(seed))
