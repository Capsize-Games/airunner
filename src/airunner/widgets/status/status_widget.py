from PyQt6.QtCore import QTimer

import psutil
import torch

from airunner.enums import SignalCode
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.status.templates.status_ui import Ui_status_widget


class StatusWidget(BaseWidget):
    widget_class_ = Ui_status_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(SignalCode.APPLICATION_STATUS_INFO_SIGNAL, self.on_status_info_signal)
        self.register(SignalCode.APPLICATION_STATUS_ERROR_SIGNAL, self.on_status_error_signal)
        self.register(SignalCode.APPLICATION_CLEAR_STATUS_MESSAGE_SIGNAL, self.on_clear_status_message_signal)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_system_stats)
        self.timer.start(100)

    def on_status_info_signal(self, message):
        self.set_system_status(message, error=False)

    def on_status_error_signal(self, message):
        self.set_system_status(message, error=True)

    def on_clear_status_message_signal(self, _ignore):
        self.set_system_status("", error=False)

    def update_system_stats(self, queue_size=0):
        nsfw_filter = self.settings["nsfw_filter"]
        has_cuda = torch.cuda.is_available()
        nsfw_status = f"NSFW Filter {'On' if nsfw_filter else 'Off'}"
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

        self.ui.nsfw_status.setStyleSheet(enabled_css if nsfw_filter else disabled_css)
        self.ui.cuda_status.setStyleSheet(enabled_css if has_cuda else disabled_css)

    def set_system_status(self, txt, error):
        self.ui.system_message.setText(txt)
        if error:
            self.ui.system_message.setStyleSheet("QLabel { color: #ff0000; }")
        else:
            self.ui.system_message.setStyleSheet("QLabel { color: #ffffff; }")
