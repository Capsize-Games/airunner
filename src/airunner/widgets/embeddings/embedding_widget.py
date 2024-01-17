from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.embeddings.templates.embedding_ui import Ui_embedding
from PyQt6.QtWidgets import QApplication


class EmbeddingWidget(BaseWidget):
    widget_class_ = Ui_embedding

    def __init__(self, *args, **kwargs):
        self.embedding = kwargs.pop("embedding")
        super().__init__(*args, **kwargs)
        self.ui.enabledCheckbox.setChecked(self.embedding["active"])
        self.ui.enabledCheckbox.setTitle(self.embedding["name"])
        if self.embedding["tags"]:
            self.ui.tags.show()
            self.ui.tags.setText(self.embedding["tags"])
        else:
            self.ui.tags.hide()

    def action_clicked_button_to_prompt(self):
        val = f"{self.app.settings['generator_settings']['prompt']} {self.embedding['name']}"
        settings = self.app.settings
        settings["generator_settings"]["prompt"] = val
        self.app.settings = settings

    def action_clicked_button_to_negative_prompt(self):
        val = f"{self.app.settings['generator_settings']['negative_prompt']} {self.embedding['name']}"
        settings = self.app.settings
        settings["generator_settings"]["negative_prompt"] = val
        self.app.settings = settings

    def action_toggled_embedding(self, val):
        self.embedding['active'] = val

    def action_clicked_copy(self):
        # copy embedding name to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(self.embedding["name"])