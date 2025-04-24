from PySide6.QtCore import Slot
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.huggingface_settings.templates.huggingface_settings_ui import (
    Ui_huggingface_settings_widget,
)


class HuggingfaceSettingsWidget(BaseWidget):
    widget_class_ = Ui_huggingface_settings_widget

    @Slot(bool)
    def on_toggle_allow_huggingface(self, val: bool):
        self.update_application_settings("allow_huggingface_downloads", val)

    @Slot(str)
    def on_huggingface_api_change(self, val: str):
        pass
