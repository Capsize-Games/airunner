from PySide6.QtCore import Slot
from PySide6.QtWidgets import QMessageBox

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.art.data.embedding import Embedding
from airunner.components.art.gui.widgets.embeddings.embedding_trigger_word_widget import (
    EmbeddingTriggerWordWidget,
)
from airunner.components.art.gui.widgets.embeddings.templates.embedding_ui import (
    Ui_embedding,
)


class EmbeddingWidget(BaseWidget):
    """
    This class represents a single embedding.
    It is responsible for displaying the embedding's name, trigger words,
    and active status.
    """

    widget_class_ = Ui_embedding
    icons = (("trash-2", "delete_button"),)

    def __init__(self, *args, **kwargs):
        self.embedding: Embedding = kwargs.pop("embedding")
        super().__init__(*args, **kwargs)
        name = self.embedding.name
        enabled = self.embedding.active
        trigger_word = self.embedding.trigger_word
        self.ui.enabled_checkbox.blockSignals(True)
        self.ui.trigger_word_edit.blockSignals(True)
        self.ui.enabled_checkbox.setChecked(enabled)
        self.ui.trigger_word_edit.setText(trigger_word)
        self.ui.enabled_checkbox.setText(name)
        self.ui.enabled_checkbox.blockSignals(False)
        self.ui.trigger_word_edit.blockSignals(False)
        self.create_trigger_word_widgets(self.embedding)

    @Slot()
    def on_delete_button_clicked(self):
        """Ask user to confirm deletion before calling the API.

        Only proceed with deletion when the user clicks Yes.
        """
        name = getattr(self.embedding, "name", "this embedding")
        reply = QMessageBox.question(
            self,
            "Delete Embedding",
            f"Are you sure you want to delete '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.api.art.embeddings.delete(self)

    def update_embedding(self, embedding: Embedding):
        Embedding.objects.update(
            **{
                "pk": embedding.id,
                "name": embedding.name,
                "trigger_word": embedding.trigger_word,
                "active": embedding.active,
            }
        )

    @Slot(bool)
    def on_enabled_checkbox_toggled(self, val: bool):
        self.embedding.active = val
        self.ui.enabled_checkbox.blockSignals(True)
        self.ui.enabled_checkbox.setChecked(val)
        self.ui.enabled_checkbox.blockSignals(False)
        self.update_embedding(self.embedding)
        self.api.art.embeddings.status_changed()

    def create_trigger_word_widgets(self, embedding: Embedding):
        for i in reversed(range(self.ui.trigger_word_container.count())):
            widget = self.ui.trigger_word_container.itemAt(i).widget()
            if isinstance(widget, EmbeddingTriggerWordWidget):
                widget.deleteLater()
        for word in embedding.trigger_word.split(","):
            if word.strip() == "":
                continue
            widget = EmbeddingTriggerWordWidget(trigger_word=word)
            self.ui.trigger_word_container.addWidget(widget)

    @Slot(str)
    def action_changed_trigger_word(self, val):
        self.embedding.trigger_word = val
        self.create_trigger_word_widgets(self.embedding)
        self.update_embedding(self.embedding)

    def enable_embedding_widget(self):
        self.ui.enabled_checkbox.setEnabled(True)
        self.ui.delete_button.setEnabled(True)

    def disable_embedding_widget(self):
        self.ui.enabled_checkbox.setEnabled(False)
        self.ui.delete_button.setEnabled(False)
