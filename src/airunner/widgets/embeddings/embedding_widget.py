from airunner.enums import SignalCode, ServiceCode
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
        self.embedding = kwargs.pop("embedding")
        super().__init__(*args, **kwargs)
        name = self.embedding["name"]
        enabled = self.embedding["active"]
        trigger_word = self.embedding["trigger_word"]
        self.ui.enabledCheckbox.blockSignals(True)
        self.ui.trigger_word_edit.blockSignals(True)
        self.ui.enabledCheckbox.setChecked(enabled)
        self.ui.trigger_word_edit.setText(trigger_word)
        self.ui.enabledCheckbox.setTitle(name)
        self.ui.enabledCheckbox.blockSignals(False)
        self.ui.trigger_word_edit.blockSignals(False)
        self.create_trigger_word_widgets(self.embedding)

    def action_toggled_embedding(self, val):
        self.embedding['active'] = val
        self.emit(SignalCode.EMBEDDING_UPDATE_SIGNAL, self.embedding)

    def create_trigger_word_widgets(self, embedding):
        for i in reversed(range(self.ui.enabledCheckbox.layout().count())):
            widget = self.ui.enabledCheckbox.layout().itemAt(i).widget()
            if isinstance(widget, EmbeddingTriggerWordWidget):
                widget.deleteLater()
        for word in embedding["trigger_word"].split(","):
            if word.strip() == "":
                continue
            widget = EmbeddingTriggerWordWidget(trigger_word=word)
            self.ui.enabledCheckbox.layout().addWidget(widget)

    def action_changed_trigger_word(self, val):
        self.embedding["trigger_word"] = val
        self.create_trigger_word_widgets(self.embedding)
        self.emit(SignalCode.EMBEDDING_UPDATE_SIGNAL, self.embedding)
