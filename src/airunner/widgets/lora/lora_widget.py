from airunner.utils import save_session
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.lora.templates.lora_ui import Ui_lora


class LoraWidget(BaseWidget):
    widget_class_ = Ui_lora

    def __init__(self, *args, **kwargs):
        self.lora = kwargs.pop("lora", None)
        super().__init__(*args, **kwargs)
        name = self.lora.name
        enabled = self.lora.enabled
        self.ui.enabledCheckbox.setText(name)
        self.ui.enabledCheckbox.setChecked(enabled)
        self.ui.trigger_word.setText(self.lora.trigger_word)

    def action_changed_trigger_words(self, val):
        self.lora.trigger_word = val
        save_session()

    def action_toggled_lora_enabled(self, val):
        self.lora.enabled = val
        save_session()

    def set_enabled(self, val):
        self.ui.enabledCheckbox.setChecked(val)
        self.lora.enabled = val
        save_session()
