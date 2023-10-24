from airunner.utils import save_session
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.lora.lora_trigger_word_widget import LoraTriggerWordWidget
from airunner.widgets.lora.templates.lora_ui import Ui_lora


class LoraWidget(BaseWidget):
    widget_class_ = Ui_lora

    def __init__(self, *args, **kwargs):
        self.lora = kwargs.pop("lora", None)
        super().__init__(*args, **kwargs)
        name = self.lora.name
        enabled = self.lora.enabled
        self.ui.enabledCheckbox.setTitle(name)
        self.ui.enabledCheckbox.setChecked(enabled)
        self.ui.trigger_word_edit.setText(self.lora.trigger_word)
        self.create_trigger_word_widgets()

    def action_text_changed_trigger_word(self, val):
        self.lora.trigger_word = val
        save_session()

    def create_trigger_word_widgets(self):
        for i in reversed(range(self.ui.enabledCheckbox.layout().count())):
            widget = self.ui.enabledCheckbox.layout().itemAt(i).widget()
            if isinstance(widget, LoraTriggerWordWidget):
                widget.deleteLater()
        for word in self.lora.trigger_word.split(","):
            if word.strip() == "":
                continue
            widget = LoraTriggerWordWidget(trigger_word=word)
            self.ui.enabledCheckbox.layout().addWidget(widget)

    def action_changed_trigger_words(self, val):
        self.lora.trigger_word = val
        save_session()
        self.create_trigger_word_widgets()

    def action_toggled_lora_enabled(self, val):
        self.lora.enabled = val
        save_session()

    def set_enabled(self, val):
        self.ui.enabledCheckbox.setChecked(val)
        self.lora.enabled = val
        save_session()