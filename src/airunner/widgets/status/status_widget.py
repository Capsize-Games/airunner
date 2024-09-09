import torch
from PySide6.QtCore import QTimer
import psutil
from PySide6.QtWidgets import QApplication
from airunner.enums import SignalCode, ModelStatus, ModelType, StatusColors
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.status.templates.status_ui import Ui_status_widget


class StatusWidget(BaseWidget):
    widget_class_ = Ui_status_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(SignalCode.APPLICATION_STATUS_INFO_SIGNAL, self.on_status_info_signal)
        self.register(SignalCode.APPLICATION_STATUS_ERROR_SIGNAL, self.on_status_error_signal)
        self.register(SignalCode.APPLICATION_CLEAR_STATUS_MESSAGE_SIGNAL, self.on_clear_status_message_signal)
        self.register(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self.on_model_status_changed_signal)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_system_stats)
        self.timer.start(1000)

        self.safety_checker_status = ModelStatus.UNLOADED
        self.feature_extractor_status = ModelStatus.UNLOADED

        settings = self.settings
        if settings["nsfw_filter"] and settings["sd_enabled"]:
            self.safety_checker_status = ModelStatus.LOADING
            self.feature_extractor_status = ModelStatus.LOADING

        self.update_safety_checker_status()
        self.update_system_stats()

    def showEvent(self, event):
        super().showEvent(event)
        self.set_sd_status_text(self.settings)

        settings = self.settings
        if settings["sd_enabled"]:
            self.on_model_status_changed_signal({
                "model": ModelType.SD,
                "status": ModelStatus.LOADING,
                "path": ""
            })
        if settings["controlnet_enabled"]:
            self.on_model_status_changed_signal({
                "model": ModelType.CONTROLNET,
                "status": ModelStatus.LOADING,
                "path": ""
            })
        if settings["llm_enabled"]:
            self.on_model_status_changed_signal({
                "model": ModelType.LLM,
                "status": ModelStatus.LOADING,
                "path": ""
            })
        if settings["tts_enabled"]:
            self.on_model_status_changed_signal({
                "model": ModelType.TTS,
                "status": ModelStatus.LOADING,
                "path": ""
            })
        if settings["stt_enabled"]:
            self.on_model_status_changed_signal({
                "model": ModelType.STT,
                "status": ModelStatus.LOADING,
                "path": ""
            })

    def update_model_status(self, data):
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

        tool_tip += " " + data["status"].value

        if element_name != "":
            getattr(self.ui, element_name).setStyleSheet(styles)
            getattr(self.ui, element_name).setToolTip(tool_tip)

    def set_sd_status_text(self, settings=None):
        settings = settings or self.settings
        self.ui.sd_status.setText(settings["generator_settings"]["version"])

    def on_model_status_changed_signal(self, data):
        self.update_model_status(data)
        model = data["model"]
        if model == ModelType.SAFETY_CHECKER:
            self.safety_checker_status = data["status"]
            self.update_safety_checker_status()
        elif model == ModelType.FEATURE_EXTRACTOR:
            self.feature_extractor_status = data["status"]
            self.update_safety_checker_status()

    def on_status_info_signal(self, message):
        self.set_system_status(message, error=False)

    def on_status_error_signal(self, message):
        self.set_system_status(message, error=True)

    def on_clear_status_message_signal(self):
        self.set_system_status("", error=False)

    def update_system_stats(self):
        cuda_status = f"{'NVIDIA' if torch.cuda.is_available() else 'CPU'}"

        # Color by has_cuda red for disabled, green for enabled
        color = StatusColors.LOADED if torch.cuda.is_available() else StatusColors.FAILED
        self.ui.cuda_status.setStyleSheet(
            "QLabel { color: " + color.value + "; }"
        )

        self.ui.cuda_status.setText(cuda_status)

    def update_safety_checker_status(self):
        # Color by safety checker status red, yellow, green for failed, loading, loaded
        if self.safety_checker_status == ModelStatus.LOADING:
            color = StatusColors.LOADING
        elif self.safety_checker_status == ModelStatus.LOADED:
            color = StatusColors.LOADED
        elif self.safety_checker_status == ModelStatus.UNLOADED:
            color = StatusColors.UNLOADED
        else:
            color = StatusColors.FAILED

        self.ui.nsfw_status.setText(
            f"Safety Checker {self.safety_checker_status.value}"
        )
        self.ui.nsfw_status.setStyleSheet(
            "QLabel { color: " + color.value + "; }"
        )

    def set_system_status(self, txt, error):
        if type(txt) is dict:
            txt = ""
        self.ui.system_message.setText(txt)
        if error:
            self.ui.system_message.setStyleSheet("QLabel { color: #ff0000; }")
        else:
            self.ui.system_message.setStyleSheet("QLabel { color: #ffffff; }")
        QApplication.processEvents()
