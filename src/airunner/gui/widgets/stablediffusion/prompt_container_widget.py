from typing import Dict
from PySide6.QtCore import Slot

from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.stablediffusion.templates.prompt_container_ui import (
    Ui_prompt_container_widget
)
from airunner.enums import SignalCode, StableDiffusionVersion


class PromptContainerWidget(BaseWidget):
    widget_class_ = Ui_prompt_container_widget
    prompt_id: int = None

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.WIDGET_ELEMENT_CHANGED: self.on_widget_element_changed,
        }
        super().__init__(*args, **kwargs)
        self._sd_version: str = self.generator_settings.version
        self._toggle_sdxl_form_elements()

    @property
    def is_sd_xl_or_turbo(self) -> bool:
        return (
            self._sd_version == StableDiffusionVersion.SDXL1_0.value or
            self._sd_version == StableDiffusionVersion.SDXL_TURBO.value
        )

    @Slot()
    def handle_delete_prompt_clicked(self):
        self.api.delete_prompt(self.prompt_id)
    
    def on_widget_element_changed(self, data: Dict):
        if data.get("element") in (
            "sd_version",
        ):
            self._sd_version = data.get("version")
            self._toggle_sdxl_form_elements()

    def _toggle_sdxl_form_elements(self):
        if self.is_sd_xl_or_turbo:
            self.ui.secondary_prompt.show()
        else:
            self.ui.secondary_prompt.hide()

    def get_prompt(self):
        """Get the current prompt text from the widget."""
        return self.ui.prompt.toPlainText()

    def set_prompt(self, text):
        """Set the prompt text in the widget."""
        self.ui.prompt.setPlainText(text)
    
    def get_prompt_secondary(self):
        """Get the current secondary prompt text from the widget."""
        return self.ui.secondary_prompt.toPlainText()
    
    def set_prompt_secondary(self, text):
        """Set the secondary prompt text in the widget."""
        self.ui.secondary_prompt.setPlainText(text)