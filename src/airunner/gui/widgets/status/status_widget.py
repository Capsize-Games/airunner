from typing import Optional, Dict
import torch
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from airunner.enums import SignalCode, ModelStatus, ModelType, StatusColors
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.status.templates.status_ui import Ui_status_widget
from airunner.settings import AIRUNNER_ART_ENABLED


class StatusWidget(BaseWidget):
    widget_class_ = Ui_status_widget

    def __init__(self, *args, **kwargs):
        self._model_status = {
            model_type: ModelStatus.UNLOADED for model_type in ModelType
        }
        self.signal_handlers = {
            SignalCode.APPLICATION_STATUS_INFO_SIGNAL: self.on_status_info_signal,
            SignalCode.APPLICATION_STATUS_ERROR_SIGNAL: self.on_status_error_signal,
            SignalCode.APPLICATION_CLEAR_STATUS_MESSAGE_SIGNAL: self.on_clear_status_message_signal,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.SD_PIPELINE_LOADED_SIGNAL: self.set_sd_pipeline_label,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed,
        }
        super().__init__(*args, **kwargs)

        if not AIRUNNER_ART_ENABLED:
            self.ui.sd_status.deleteLater()
            self.ui.controlnet_status.deleteLater()
            self.ui.nsfw_status.deleteLater()

        self.set_sd_pipeline_label()
        self.version = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_system_stats)
        self.timer.start(1000)

        self.safety_checker_status = ModelStatus.UNLOADED
        self.feature_extractor_status = ModelStatus.UNLOADED

        if (
            self.application_settings.nsfw_filter
            and self.application_settings.sd_enabled
        ):
            self.safety_checker_status = ModelStatus.LOADING
            self.feature_extractor_status = ModelStatus.LOADING

        self.update_system_stats()

        for item in [
            (ModelType.LLM, "llm_enabled"),
            (ModelType.TTS, "tts_enabled"),
            (ModelType.STT, "stt_enabled"),
            (ModelType.SD, "sd_enabled"),
            (ModelType.CONTROLNET, "controlnet_enabled"),
        ]:
            if getattr(self.application_settings, item[1]):
                self._model_status[item[0]] = ModelStatus.LOADING
                self.update_model_status(
                    {"model": item[0], "status": ModelStatus.LOADING}
                )

    def on_application_settings_changed(self):
        self.set_sd_status_text()

    def set_sd_pipeline_label(self, data: Optional[Dict] = None):
        data = data or {}
        if data.get("generator_section", None):
            self.ui.pipeline_label.setText(data["generator_section"].value)
            self.ui.pipeline_divider.show()
        else:
            self.ui.pipeline_label.setText("")
            self.ui.pipeline_divider.hide()

    def showEvent(self, event):
        super().showEvent(event)
        self.set_sd_status_text()

        if self.application_settings.sd_enabled:
            self.on_model_status_changed_signal(
                {
                    "model": ModelType.SD,
                    "status": self._model_status[ModelType.SD],
                    "path": "",
                }
            )
        if self.application_settings.controlnet_enabled:
            self.on_model_status_changed_signal(
                {
                    "model": ModelType.CONTROLNET,
                    "status": self._model_status[ModelType.CONTROLNET],
                    "path": "",
                }
            )
        if self.application_settings.llm_enabled:
            self.on_model_status_changed_signal(
                {
                    "model": ModelType.LLM,
                    "status": self._model_status[ModelType.LLM],
                    "path": "",
                }
            )
        if self.application_settings.tts_enabled:
            self.on_model_status_changed_signal(
                {
                    "model": ModelType.TTS,
                    "status": self._model_status[ModelType.TTS],
                    "path": "",
                }
            )
        if self.application_settings.stt_enabled:
            self.on_model_status_changed_signal(
                {
                    "model": ModelType.STT,
                    "status": self._model_status[ModelType.STT],
                    "path": "",
                }
            )
        if (
            self.application_settings.nsfw_filter
            and self.application_settings.sd_enabled
        ):
            self.on_model_status_changed_signal(
                {
                    "model": ModelType.SAFETY_CHECKER,
                    "status": self._model_status[ModelType.SAFETY_CHECKER],
                    "path": "",
                }
            )

    def update_model_status(self, data):
        self._model_status[data["model"]] = data["status"]
        if data["status"] is ModelStatus.LOADING:
            color = StatusColors.LOADING
        elif data["status"] is ModelStatus.LOADED:
            color = StatusColors.LOADED
        elif data["status"] is ModelStatus.FAILED:
            color = StatusColors.FAILED
        elif data["status"] is ModelStatus.READY:
            color = StatusColors.READY
        else:
            color = StatusColors.UNLOADED

        styles = "QLabel { color: " + color.value + "; }"
        element_name = ""
        tool_tip = ""
        if not data["model"]:
            return
        if data["model"] == ModelType.SD:
            element_name = "sd_status"
            tool_tip = "Stable Diffusion"
            self.set_sd_status_text()
        elif data["model"] == ModelType.CONTROLNET:
            element_name = "controlnet_status"
            tool_tip = "Controlnet"
        elif data["model"] == ModelType.LLM:
            element_name = "llm_status"
            tool_tip = "LLM"
        elif data["model"] == ModelType.TTS:
            element_name = "tts_status"
            tool_tip = "TTS"
        elif data["model"] == ModelType.STT:
            element_name = "stt_status"
            tool_tip = "STT"
        elif data["model"] == ModelType.SAFETY_CHECKER:
            element_name = "nsfw_status"
            tool_tip = "Safety Checker"

        tool_tip += " " + data["status"].value

        if element_name != "":
            getattr(self.ui, element_name).setStyleSheet(styles)
            getattr(self.ui, element_name).setToolTip(tool_tip)
        QApplication.processEvents()

    def set_sd_status_text(self):
        if self.version != self.generator_settings.version:
            version = self.generator_settings.version
            try:
                self.ui.sd_status.setText(version)
            except RuntimeError as e:
                if AIRUNNER_ART_ENABLED:
                    self.logger.warning(f"Error setting SD status text: {e}")

    def on_model_status_changed_signal(self, data):
        self.update_model_status(data)

    def on_status_info_signal(self, message):
        self.logger.info(message)
        self.set_system_status(message, error=False)

    def on_status_error_signal(self, message):
        self.set_system_status(message, error=True)

    def on_clear_status_message_signal(self):
        self.set_system_status("", error=False)

    def update_system_stats(self):
        cuda_status = f"{'NVIDIA' if torch.cuda.is_available() else 'CPU'}"

        # Color by has_cuda red for disabled, green for enabled
        color = (
            StatusColors.LOADED
            if torch.cuda.is_available()
            else StatusColors.FAILED
        )
        self.ui.cuda_status.setStyleSheet(
            "QLabel { color: " + color.value + "; }"
        )

        self.ui.cuda_status.setText(cuda_status)

    def set_system_status(self, txt, error):
        if type(txt) is dict:
            txt = ""
        self.ui.system_message.setText(txt)
        if error:
            self.ui.system_message.setStyleSheet("QLabel { color: #ff0000; }")
        else:
            self.ui.system_message.setStyleSheet("QLabel { color: #ffffff; }")
        QApplication.processEvents()
