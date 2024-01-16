from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.seed.templates.seed_ui import Ui_seed_widget


class SeedWidget(BaseWidget):
    seed = 42
    widget_class_ = Ui_seed_widget
    name = "seed_widget"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.app.application_settings_changed_signal.connect(self.update_seed)

    def update_seed(self):
        self.ui.lineEdit.setText(str(self.seed))

    def action_clicked_button_random_seed(self, value):
        property_name = self.property("property_name")
        self.app.settings_manager.set_value(property_name, value)
        self.ui.lineEdit.setEnabled(not value)

    def action_value_changed_seed(self, value):
        self.seed = value
