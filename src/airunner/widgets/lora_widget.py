from functools import partial
from airunner.widgets.base_widget import BaseWidget


class LoraWidget(BaseWidget):
    name = "lora"

    def __init__(self, *args, **kwargs):
        self.lora = kwargs.pop("lora", None)
        super().__init__(*args, **kwargs)
        name = self.lora["name"]
        enabled = self.lora["enabled"]
        self.enabledCheckbox.setText(name)
        self.enabledCheckbox.setChecked(enabled)
        self.setStyleSheet("""
        font-size: 9pt;
        """)
        self.trigger_word.setStyleSheet("""
        border-radius: 0px;
        border: 1px solid #1f1f1f;
        """)