import os

import psutil
import torch
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QTableWidgetItem, QApplication
from airunner.enums import SignalCode
from airunner.gui.styles.styles_mixin import StylesMixin
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.stats.templates.stats_ui import Ui_stats_widget
from airunner.gui.windows.main.pipeline_mixin import PipelineMixin
from airunner.utils.memory.gpu_memory_stats import gpu_memory_stats


class StatsWidget(
    BaseWidget,
    PipelineMixin,
    StylesMixin
):
    widget_class_ = Ui_stats_widget

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.LOG_LOGGED_SIGNAL: self.on_log_logged_signal,
        }
        super().__init__(*args, **kwargs)

        # Track console history
        self.console_history = []

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_memory_stats)
        self.timer.start(500)

    def showEvent(self, event):
        super().showEvent(event)
        self.set_stylesheet()

    def update_memory_stats(self):
        # Clear the table
        headers = ["Device", "Used Memory", "Total Memory", "Free Memory"]
        col_count = len(headers)

        # Get GPU details
        device_count = torch.cuda.device_count()
        row_count = device_count + 1  # Add 1 for CPU

        self.ui.memory_stats.setColumnCount(col_count)
        self.ui.memory_stats.setRowCount(row_count)
        self.ui.memory_stats.setHorizontalHeaderLabels(headers)

        for i in range(device_count):
            device = torch.device(f'cuda:{i}')
            
            try:
                torch.cuda.set_device(device)
            except RuntimeError as e:
                self.logger.error(f"Error setting device: {e}")
                continue
                
            
            stats = gpu_memory_stats(device)
            total_mem = stats["total"]
            allocated_mem = stats["allocated"]
            free_mem = stats["free"]
            device_name = stats["device_name"]

            # truncate to 2 decimal places
            total_mem = round(total_mem, 2)
            allocated_mem = round(allocated_mem, 2)
            free_mem = round(free_mem, 2)

            self.ui.memory_stats.setItem(i, 0, QTableWidgetItem(device_name))
            self.ui.memory_stats.setItem(i, 1, QTableWidgetItem(f"{allocated_mem}GB"))
            self.ui.memory_stats.setItem(i, 2, QTableWidgetItem(f"{total_mem}GB"))
            self.ui.memory_stats.setItem(i, 3, QTableWidgetItem(f"{free_mem}GB"))

            # Set colors
            self.ui.memory_stats.item(i, 1).setForeground(Qt.GlobalColor.red)
            self.ui.memory_stats.item(i, 2).setForeground(Qt.GlobalColor.yellow)
            self.ui.memory_stats.item(i, 3).setForeground(Qt.GlobalColor.green)

        # Get memory details for the current process
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
        except Exception as _e:
            return

        used = memory_info.rss / (1024.0 ** 3)  # Resident Set Size
        total = psutil.virtual_memory().total / (1024.0 ** 3)
        available = total - used

        # truncate to 2 decimal places
        used = round(used, 2)
        total = round(total, 2)
        available = round(available, 2)

        self.ui.memory_stats.setItem(row_count - 1, 0, QTableWidgetItem("CPU"))
        self.ui.memory_stats.setItem(row_count - 1, 1, QTableWidgetItem(f"{used}GB"))
        self.ui.memory_stats.setItem(row_count - 1, 2, QTableWidgetItem(f"{total}GB"))
        self.ui.memory_stats.setItem(row_count - 1, 3, QTableWidgetItem(f"{available}GB"))

        # Set colors
        self.ui.memory_stats.item(row_count - 1, 1).setForeground(Qt.GlobalColor.red)
        self.ui.memory_stats.item(row_count - 1, 2).setForeground(Qt.GlobalColor.yellow)
        self.ui.memory_stats.item(row_count - 1, 3).setForeground(Qt.GlobalColor.green)

        QApplication.processEvents()

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
        QApplication.processEvents()
