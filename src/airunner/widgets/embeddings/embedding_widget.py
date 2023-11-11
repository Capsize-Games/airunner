from airunner.utils import save_session
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.embeddings.templates.embedding_ui import Ui_embedding


class EmbeddingWidget(BaseWidget):
    widget_class_ = Ui_embedding
    embedding = None

    def __init__(self, *args, **kwargs):
        self.embedding = kwargs.pop("embedding")
        super().__init__(*args, **kwargs)
        self.ui.enabledCheckbox.setChecked(self.embedding.active)
        self.ui.enabledCheckbox.setTitle(self.embedding.name)
        if self.embedding.tags:
            self.ui.tags.show()
            self.ui.tags.setText(", ".join(self.embedding.tags))
        else:
            self.ui.tags.hide()

    def action_clicked_button_to_prompt(self):
        val = f"{self.settings_manager.generator.prompt} {self.embedding.name}"
        self.settings_manager.set_value("generator.prompt", val)

    def action_clicked_button_to_negative_prompt(self):
        val = f"{self.settings_manager.generator.negative_prompt} {self.embedding.name}"
        self.settings_manager.set_value("generator.negative_prompt", val)

    def action_toggled_embedding(self, val):
        self.embedding.active = val
        save_session()
