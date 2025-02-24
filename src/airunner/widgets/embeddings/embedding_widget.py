from PySide6.QtCore import Slot

from airunner.data.models import Embedding
from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.embeddings.embedding_trigger_word_widget import EmbeddingTriggerWordWidget
from airunner.widgets.embeddings.templates.embedding_ui import Ui_embedding


class EmbeddingWidget(BaseWidget):
    """
    This class represents a single embedding.
    It is responsible for displaying the embedding's name, trigger words,
    and active status.
    """
    widget_class_ = Ui_embedding

    def __init__(self, *args, **kwargs):
        self.embedding: Embedding = kwargs.pop("embedding")
        super().__init__(*args, **kwargs)
        name = self.embedding.name
        enabled = self.embedding.active
        trigger_word = self.embedding.trigger_word
        self.ui.enabledCheckbox.blockSignals(True)
        self.ui.trigger_word_edit.blockSignals(True)
        self.ui.enabledCheckbox.setChecked(enabled)
        self.ui.trigger_word_edit.setText(trigger_word)
        self.ui.enabledCheckbox.setText(name)
        self.ui.enabledCheckbox.blockSignals(False)
        self.ui.trigger_word_edit.blockSignals(False)
        self.create_trigger_word_widgets(self.embedding)

    @Slot()
    def action_clicked_button_deleted(self):
        self.emit_signal(
            SignalCode.EMBEDDING_DELETE_SIGNAL,
            {
                "embedding_widget": self
            }
        )

    def update_embedding(self, embedding: Embedding):
        self.save_object(embedding)

    @Slot(bool)
    def action_toggled_embedding(self, val, emit_signal=True):
        self.embedding.active = val
        self.ui.enabledCheckbox.blockSignals(True)
        self.ui.enabledCheckbox.setChecked(val)
        self.ui.enabledCheckbox.blockSignals(False)
        self.update_embedding(self.embedding)
        self.emit_signal(SignalCode.EMBEDDING_STATUS_CHANGED)

    def create_trigger_word_widgets(self, embedding: Embedding):
        for i in reversed(range(self.ui.gridLayout.layout().count())):
            widget = self.ui.gridLayout.layout().itemAt(i).widget()
            if isinstance(widget, EmbeddingTriggerWordWidget):
                widget.deleteLater()
        for word in embedding.trigger_word.split(","):
            if word.strip() == "":
                continue
            widget = EmbeddingTriggerWordWidget(trigger_word=word)
            self.ui.gridLayout.layout().addWidget(widget)

    @Slot(str)
    def action_changed_trigger_word(self, val):
        self.embedding.trigger_word = val
        self.create_trigger_word_widgets(self.embedding)
        self.update_embedding(self.embedding)

    def enable_embedding_widget(self):
        self.ui.enabledCheckbox.setEnabled(True)
        self.ui.delete_button.setEnabled(True)

    def disable_embedding_widget(self):
        self.ui.enabledCheckbox.setEnabled(False)
        self.ui.delete_button.setEnabled(False)
