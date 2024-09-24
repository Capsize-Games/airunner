from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.lora.templates.lora_trigger_word_ui import Ui_lora_trigger_word
from PySide6.QtWidgets import QApplication


class LoraTriggerWordWidget(BaseWidget):
    widget_class_ = Ui_lora_trigger_word
    trigger_word = None

    def __init__(self, *args, **kwargs):
        self.trigger_word = kwargs.pop("trigger_word")
        super().__init__(*args, **kwargs)
        self.ui.trigger_word.setText(self.trigger_word)

    def action_click_button_to_prompt(self):
        self.update_generator_settings("prompt", f"{self.generator_settings.prompt} {self.trigger_word}")
        self.emit_signal(SignalCode.GENERATOR_FORM_UPDATE_VALUES_SIGNAL)

    def action_click_button_to_negative_prompt(self):
        self.update_generator_settings("negative_prompt", f"{self.generator_settings.negative_prompt} {self.trigger_word}")
        self.emit_signal(SignalCode.GENERATOR_FORM_UPDATE_VALUES_SIGNAL)
    
    def action_click_button_copy(self):
        # copy trigger word to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(self.trigger_word)
