from typing import Any
from PySide6.QtCore import Slot

from airunner.components.llm.gui.widgets.templates.rag_settings_ui import \
    Ui_rag_settings
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.llm.data.rag_settings import RAGSettings
from airunner.enums import ModelService


class RAGSettingsWidget(BaseWidget):
    widget_class_ = Ui_rag_settings

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui.service.blockSignals(True)
        self.ui.service.clear()
        self.ui.service.addItems(
            [
                ModelService.LOCAL.value,
                ModelService.HUGGINGFACE.value,
                ModelService.OPENROUTER.value,
            ]
        )
        service = self.rag_settings.model_service
        self.ui.service.setCurrentText(service)
        self.ui.service.blockSignals(False)
        self.toggle_model_path_visibility(service)

    @Slot(str)
    def on_service_currentTextChanged(self, text: str):
        self.ui.model_path.setEnabled(text == ModelService.LOCAL.value)
        self.update_rag_settings("model_service", text)
        self.toggle_model_path_visibility(text)

    @Slot(str)
    def on_model_path_textChanged(self, text: str):
        self.update_rag_settings("model_path", text)
        RAGSettings.objects.update(
            self.rag_settings.id,
            model_path=text,
        )

    def toggle_model_path_visibility(self, service: str = ""):
        if service == ModelService.LOCAL.value:
            self.ui.model_path_container.hide()
        else:
            self.ui.model_path.blockSignals(True)
            self.ui.model_path.setText(self.rag_settings.model_path)
            self.ui.model_path_container.show()
            self.ui.model_path.blockSignals(False)

    def update_rag_settings(self, key: str, value: Any):
        setattr(self.rag_settings, key, value)
        RAGSettings.objects.update(
            self.rag_settings.id,
            **{key: value},
        )
