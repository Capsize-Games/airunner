import os

import psutil
import torch
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QTableWidgetItem
from airunner.enums import SignalCode
from airunner.gui.styles.styles_mixin import StylesMixin
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.application.gui.widgets.stats.templates.stats_ui import (
    Ui_stats_widget,
)
from airunner.components.application.gui.windows.main.pipeline_mixin import (
    PipelineMixin,
)
from airunner.utils.memory.gpu_memory_stats import gpu_memory_stats


class StatsWidget(BaseWidget, PipelineMixin, StylesMixin):
    ui: Ui_stats_widget  # type: ignore[assignment]
    widget_class_ = Ui_stats_widget

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.LOG_LOGGED_SIGNAL: self.on_log_logged_signal,
        }
        self._gpu_stats_warning_logged = False
        super().__init__(*args, **kwargs)

        # Track console history
        self.console_history = []

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_memory_stats)
        self.timer.start(50)
        self.update_memory_stats()

    def showEvent(self, event):
        super().showEvent(event)
        self.set_stylesheet()

    def update_memory_stats(self):
        """Refresh the memory usage table."""
        headers = [
            "Device",
            "Used Memory",
            "Total Memory",
            "Free Memory",
        ]
        device_count = torch.cuda.device_count()
        row_count = device_count + 1

        self.ui.memory_stats.setColumnCount(len(headers))
        self.ui.memory_stats.setRowCount(row_count)
        self.ui.memory_stats.setHorizontalHeaderLabels(headers)
        self._populate_gpu_rows(device_count)
        self._populate_cpu_row(row_count - 1)

    def _populate_gpu_rows(self, device_count: int) -> None:
        """Fill one table row per CUDA device."""
        for index in range(device_count):
            device = torch.device(f"cuda:{index}")
            try:
                stats = gpu_memory_stats(device)
            except RuntimeError as exc:
                self._log_gpu_stats_warning_once(exc)
                continue

            self._set_memory_row(
                index,
                str(stats["device_name"]),
                float(stats["used"]),
                float(stats["total"]),
                float(stats["free"]),
            )

    def _populate_cpu_row(self, row: int) -> None:
        """Fill the CPU memory row."""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
        except Exception:
            return

        used = memory_info.rss / (1024.0**3)  # Resident Set Size
        total = psutil.virtual_memory().total / (1024.0**3)
        available = total - used
        self._set_memory_row(row, "CPU", used, total, available)

    def _set_memory_row(
        self,
        row: int,
        device_name: str,
        used_mem: float,
        total_mem: float,
        free_mem: float,
    ) -> None:
        """Set one table row and apply status colors."""
        items = [
            QTableWidgetItem(device_name),
            QTableWidgetItem(f"{round(used_mem, 2)}GB"),
            QTableWidgetItem(f"{round(total_mem, 2)}GB"),
            QTableWidgetItem(f"{round(free_mem, 2)}GB"),
        ]
        for column, item in enumerate(items):
            self.ui.memory_stats.setItem(row, column, item)

        self.ui.memory_stats.item(row, 1).setForeground(Qt.GlobalColor.red)
        self.ui.memory_stats.item(row, 2).setForeground(
            Qt.GlobalColor.yellow
        )
        self.ui.memory_stats.item(row, 3).setForeground(
            Qt.GlobalColor.green
        )

    def _log_gpu_stats_warning_once(self, error: Exception) -> None:
        """Log one GPU stats warning instead of spamming every refresh."""
        if self._gpu_stats_warning_logged:
            return
        self._gpu_stats_warning_logged = True
        self.logger.warning(f"GPU stats unavailable: {error}")

    def closeEvent(self, event):
        """Stop background polling when the stats window closes."""
        if self.timer.isActive():
            self.timer.stop()
        super().closeEvent(event)

    @staticmethod
    def set_color(_row, _col, status):
        pass

    def on_log_logged_signal(self, data: dict = None):
        """
        Log a message to the console.
        :param data:
        :return:
        """
        self.console_history.append(data["message"])
        self.ui.console.append(data["message"])
