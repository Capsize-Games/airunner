from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.embeddings.templates.embedding_ui import Ui_embedding


class EmbeddingWidget(BaseWidget):
    widget_class_ = Ui_embedding

    def __init__(self, *args, **kwargs):
        self.name = kwargs.pop("name", None)
        self.tags = kwargs.pop("tags", [])
        self.active = kwargs.pop("active", True)
        super().__init__(*args, **kwargs)
        self.ui.name.checked = self.active
        self.ui.name.setTitle(self.name)
        if len(self.tags):
            self.ui.tags.show()
            self.ui.tags.setText(", ".join(self.tags))
        else:
            self.ui.tags.hide()

    def action_clicked_button_to_prompt(self):
        self.app.insert_into_prompt(f"{self.name}")

    def action_clicked_button_to_negative_prompt(self):
        self.app.insert_into_prompt(f"{self.name}", True)
