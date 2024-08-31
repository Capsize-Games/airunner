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

    def on_model_status_changed_signal(self, data):
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

    def on_clear_status_message_signal(self, _ignore):
        self.set_system_status("", error=False)

    def update_system_stats(self, queue_size=0):
        queue_stats = f"Queued items: {queue_size}"
        cuda_status = f"{'NVIDIA' if torch.cuda.is_available() else 'CPU'}"

        # Color by has_cuda red for disabled, green for enabled
        color = StatusColors.LOADED if torch.cuda.is_available() else StatusColors.FAILED
        self.ui.cuda_status.setStyleSheet(
            "QLabel { color: " + color.value + "; }"
        )

        self.ui.cuda_status.setText(cuda_status)
        self.ui.queue_stats.setText(queue_stats)

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
