from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.seed.templates.seed_ui import Ui_seed_widget


class SeedWidget(BaseWidget):
    seed = 42
    widget_class_ = Ui_seed_widget
    name = "seed_widget"

    # def initialize(self, generator_section, generator_name):
    #     self.ui.lineEdit.setText(str(self.seed))
    #     self.settings_manager.generator_section = generator_section
    #     self.settings_manager.generator_name = generator_name
    #     self.ui.random_button.setChecked(self.settings_manager.generator.random_seed)
    #     self.ui.lineEdit.setEnabled(not self.settings_manager.generator.random_seed)

    def update_seed(self):
        self.ui.lineEdit.setText(str(self.seed))

    def action_clicked_button_random_seed(self, value):
        property_name = self.property("property_name")
        self.settings_manager.set_value(property_name, value)
        self.ui.lineEdit.setEnabled(not value)

    def action_value_changed_seed(self, value):
        self.seed = value


class LatentsSeedWidget(SeedWidget):
    setting_name = "generator.random_latents_seed"

    # def initialize(self, generator_section, generator_name):
    #     self.settings_manager.generator_section = generator_section
    #     self.settings_manager.generator_name = generator_name
    #     self.ui.label.setText("Image Seed")
    #     self.update_seed()
    #     self.ui.random_button.setChecked(self.settings_manager.generator.random_latents_seed)
    #     self.ui.lineEdit.setEnabled(not self.settings_manager.generator.random_latents_seed)
