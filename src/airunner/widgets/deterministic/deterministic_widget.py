from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.deterministic.templates.deterministic_widget_ui import Ui_deterministic_widget


class DeterministicWidget(BaseWidget):
    widget_class_ = Ui_deterministic_widget

    @property
    def batch_size(self):
        return self.ui.images_per_batch.value()

    @property
    def category(self):
        return self.ui.category.text()

    def action_value_changed_images_per_batch(self, val):
        self.settings_manager.set_value("determinisitic_settings.images_per_batch", val)

    def action_text_changed_category(self, val):
        self.settings_manager.set_value("determinisitic_settings.category", val)

    def action_clicked_button_generate_batch(self):
        print("generate batch clicked")
