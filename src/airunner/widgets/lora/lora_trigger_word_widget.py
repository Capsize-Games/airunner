from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.lora.templates.lora_trigger_word_ui import Ui_lora_trigger_word


class LoraTriggerWordWidget(BaseWidget):
    widget_class_ = Ui_lora_trigger_word
    trigger_word = None

    def __init__(self, *args, **kwargs):
        self.trigger_word = kwargs.pop("trigger_word")
        super().__init__(*args, **kwargs)
        self.ui.trigger_word.setText(self.trigger_word)

    def action_click_button_to_prompt(self):
        self.settings_manager.set_value(
            "generator.prompt",
            f"{self.settings_manager.generator.prompt} {self.trigger_word}"
        )

    def action_click_button_to_negative_prompt(self):
        self.settings_manager.set_value(
            "generator.negative_prompt",
            f"{self.settings_manager.generator.negative_prompt} {self.trigger_word}"
        )