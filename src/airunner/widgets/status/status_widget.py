from PySide6.QtCore import QTimer
import psutil
from PySide6.QtWidgets import QApplication

from airunner.enums import SignalCode, ModelStatus, ModelType
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
        self.safety_checker_status = ModelStatus.UNLOADED

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_system_stats)
        self.timer.start(1000)

        self.safety_checker_status = ModelStatus.UNLOADED
        self.feature_extractor_status = ModelStatus.UNLOADED

    def on_model_status_changed_signal(self, data):
        model = data["model"]
        if model == ModelType.SAFETY_CHECKER:
            self.safety_checker_status = data["status"]
            self.update_system_stats()
        else:
            self.feature_extractor_status = data["status"]
            self.update_system_stats()

    def on_status_info_signal(self, message):
        self.set_system_status(message, error=False)

    def on_status_error_signal(self, message):
        self.set_system_status(message, error=True)

    def on_clear_status_message_signal(self, _ignore):
        self.set_system_status("", error=False)

    def update_system_stats(self, queue_size=0):
        import torch

        nsfw_filter = self.settings["nsfw_filter"]
        has_cuda = torch.cuda.is_available()
        nsfw_status = f"Safety Checker {'On' if nsfw_filter else 'Off'} and {'Loaded' if self.safety_checker_status == ModelStatus.LOADED else 'Not Loaded'}"
        if self.safety_checker_status == ModelStatus.FAILED:
            nsfw_status = "Safety Checker Failed to Load"
        queue_stats = f"Queued items: {queue_size}"
        cuda_status = f"Using {'GPU' if has_cuda else 'CPU'}"
        vram_stats = f"VRAM allocated {torch.cuda.memory_allocated() / 1024 ** 3:.1f}GB cached {torch.cuda.memory_cached() / 1024 ** 3:.1f}GB"
        ram_stats = f"RAM used {psutil.virtual_memory().percent:.1f}%"
        self.ui.nsfw_status.setText(nsfw_status)
        self.ui.cuda_status.setText(cuda_status)
        self.ui.queue_stats.setText(queue_stats)
        self.ui.vram_stats.setText(vram_stats)
        self.ui.ram_stats.setText(ram_stats)

        enabled_css = "QLabel { color: #00ff00; }"
        disabled_css = "QLabel { color: #ff0000; }"

        nsfw_filter = False if self.safety_checker_status != ModelStatus.LOADED else nsfw_filter

        self.ui.nsfw_status.setStyleSheet(enabled_css if nsfw_filter else disabled_css)
        self.ui.cuda_status.setStyleSheet(enabled_css if has_cuda else disabled_css)

    def set_system_status(self, txt, error):
        if type(txt) is dict:
            txt = ""
        self.ui.system_message.setText(txt)
        if error:
            self.ui.system_message.setStyleSheet("QLabel { color: #ff0000; }")
        else:
            self.ui.system_message.setStyleSheet("QLabel { color: #ffffff; }")
        QApplication.processEvents()

