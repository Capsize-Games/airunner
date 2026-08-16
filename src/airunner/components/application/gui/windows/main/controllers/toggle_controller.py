"""Model toggle dispatch helpers for MainWindow."""

from __future__ import annotations

from typing import Dict, Optional

from PIL import Image
from PySide6.QtWidgets import QMessageBox

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner.enums import ModelStatus, ModelType, SignalCode
from airunner.utils.image import convert_image_to_binary


class ToggleController(MainWindowBase):
    """Dispatch model load/unload toggles and error dialogs."""

    def on_toggle_llm(self, data: Optional[Dict] = None, val: Optional[bool] = None):
        data = data or {}
        if val is None:
            val = bool(data.get("enabled", not self.application_settings.llm_enabled))
        if bool(data.get("sync_only", False)):
            if bool(self.application_settings.llm_enabled) != bool(val):
                self.update_application_settings(llm_enabled=bool(val))
            return
        self._update_action_button(
            ModelType.LLM,
            None,
            bool(val),
            SignalCode.LLM_LOAD_SIGNAL,
            SignalCode.LLM_UNLOAD_SIGNAL,
            "llm_enabled",
            data,
        )

    def on_toggle_tts(self, data: Optional[Dict] = None, val: Optional[bool] = None):
        data = data or {}
        if val is None:
            val = bool(data.get("enabled", not self.application_settings.tts_enabled))
        self._update_action_button(
            ModelType.TTS,
            getattr(self.ui, "text_to_speech_button", None),
            bool(val),
            SignalCode.TTS_ENABLE_SIGNAL,
            SignalCode.TTS_DISABLE_SIGNAL,
            "tts_enabled",
            data,
        )

    def _update_action_button(
        self,
        model_type,
        element,
        val: bool,
        load_signal: SignalCode,
        unload_signal: SignalCode,
        application_setting: Optional[str] = None,
        data: Optional[Dict] = None,
    ):
        is_loading = self._model_status[model_type] is ModelStatus.LOADING
        if self._block_loading_toggle(model_type, element, is_loading, val):
            return
        if element is not None:
            self._set_action_checked_state(element, val)
        if application_setting:
            self.update_application_settings(**{application_setting: val})
        if is_loading:
            return
        self._emit_toggle_signal(load_signal, unload_signal, val, data)

    def _block_loading_toggle(
        self, model_type, element, is_loading: bool, val: bool
    ) -> bool:
        """Return True when a loading toggle must be ignored."""
        if not is_loading or self._allows_loading_toggle(model_type):
            return False
        if element is not None:
            self._set_action_checked_state(element, not val)
        return True

    def _emit_toggle_signal(
        self, load_signal, unload_signal, val: bool, data
    ) -> None:
        """Emit the appropriate load or unload signal."""
        if val:
            self.emit_signal(load_signal, data)
        else:
            self.emit_signal(unload_signal, data)

    def _generate_drawingpad_mask(self):
        width = self.application_settings.working_width
        height = self.application_settings.working_height
        img = Image.new("RGB", (width, height), (0, 0, 0))
        base64_image = convert_image_to_binary(img)
        self.update_drawing_pad_settings(mask=base64_image)

    def display_missing_models_error(self, data):
        self._show_error_dialog(
            data.get("title", "Error: Missing models"),
            data.get("message", "Something went wrong"),
        )

    def on_status_error_signal(self, data):
        self._show_error_dialog(
            data.get("title", "Error"),
            data.get("message", "Something went wrong"),
        )

    def _show_error_dialog(self, title: str, message: str) -> None:
        """Show one critical error message box."""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec()
