from airunner.data.session_scope import session_scope
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.embeddings.templates.embedding_ui import Ui_embedding
from PyQt6.QtWidgets import QApplication
from contextlib import contextmanager
from sqlalchemy.exc import InvalidRequestError

class EmbeddingWidget(BaseWidget):
    widget_class_ = Ui_embedding

    @contextmanager
    def embedding(self):
        with session_scope() as session:
            try:
                session.add(self._embedding)
            except InvalidRequestError:
                pass
            yield self._embedding

    def __init__(self, *args, **kwargs):
        self._embedding = kwargs.pop("embedding")
        super().__init__(*args, **kwargs)
        with self.embedding() as embedding:
            self.ui.enabledCheckbox.setChecked(embedding.active)
            self.ui.enabledCheckbox.setTitle(embedding.name)
            if embedding.tags:
                self.ui.tags.show()
                self.ui.tags.setText(embedding.tags)
            else:
                self.ui.tags.hide()

    def action_clicked_button_to_prompt(self):
        with self.embedding() as embedding:
            val = f"{self.app.settings['generator_settings']['prompt']} {embedding.name}"
            settings = self.app.settings
            settings["generator_settings"]["prompt"] = val
            self.app.settings = settings

    def action_clicked_button_to_negative_prompt(self):
        with self.embedding() as embedding:
            val = f"{self.app.settings['generator_settings']['negative_prompt']} {embedding.name}"
            settings = self.app.settings
            settings["generator_settings"]["negative_prompt"] = val
            self.app.settings = settings

    def action_toggled_embedding(self, val):
        with self.embedding() as embedding:
            embedding.active = val

    def action_clicked_copy(self):
        # copy embedding name to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(self.embedding.name)