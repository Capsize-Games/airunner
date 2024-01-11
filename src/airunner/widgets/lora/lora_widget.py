from airunner.data.session_scope import session_scope
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.lora.lora_trigger_word_widget import LoraTriggerWordWidget
from airunner.data.models import Lora
from airunner.widgets.lora.templates.lora_ui import Ui_lora
from contextlib import contextmanager


class LoraWidget(BaseWidget):
    widget_class_ = Ui_lora

    @contextmanager
    def lora(self):
        with session_scope() as session:
            lora = session.query(Lora).first()
            yield lora

    def __init__(self, *args, **kwargs):
        self._lora = kwargs.pop("lora", None)
        super().__init__(*args, **kwargs)
        with self.lora() as lora:
            name = lora.name
            enabled = lora.enabled
            self.ui.enabledCheckbox.setTitle(name)
            self.ui.enabledCheckbox.setChecked(enabled)
            self.ui.trigger_word_edit.setText(lora.trigger_word)
            self.create_trigger_word_widgets(lora)

    def action_text_changed_trigger_word(self, val):
        with self.lora() as lora:
            lora.trigger_word = val
        
    def create_trigger_word_widgets(self, lora):
        for i in reversed(range(self.ui.enabledCheckbox.layout().count())):
            widget = self.ui.enabledCheckbox.layout().itemAt(i).widget()
            if isinstance(widget, LoraTriggerWordWidget):
                widget.deleteLater()
        for word in lora.trigger_word.split(","):
            if word.strip() == "":
                continue
            widget = LoraTriggerWordWidget(trigger_word=word)
            self.ui.enabledCheckbox.layout().addWidget(widget)

    def action_changed_trigger_words(self, val):
        with self.lora() as lora:
            lora.trigger_word = val
            self.create_trigger_word_widgets(lora)

    def action_toggled_lora_enabled(self, val):
        with self.lora() as lora:
            lora.enabled = val
        
    def set_enabled(self, val):
        with self.lora() as lora:
            self.ui.enabledCheckbox.setChecked(val)
            lora.enabled = val