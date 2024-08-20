from functools import partial

import psutil
import torch
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtWidgets import QTableWidgetItem, QHeaderView, QApplication, QPushButton
from airunner.enums import SignalCode, ModelStatus, ModelType
from airunner.utils.clear_memory import clear_memory
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.stats.templates.stats_ui import Ui_stats_widget
from airunner.windows.main.pipeline_mixin import PipelineMixin


class StatsWidget(
    BaseWidget,
    PipelineMixin
):
    widget_class_ = Ui_stats_widget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.register(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, self.on_model_status_changed_signal)
        self.register(SignalCode.LOG_LOGGED_SIGNAL, self.on_log_logged_signal)

        # Track console history
        self.console_history = []

        model_order = [
            ModelType.SAFETY_CHECKER,
            ModelType.FEATURE_EXTRACTOR,
            ModelType.CONTROLNET_PROCESSOR,
            ModelType.CONTROLNET,
            ModelType.SCHEDULER,
            ModelType.SD_VAE,
            ModelType.SD_UNET,
            ModelType.SD_TEXT_ENCODER,
            ModelType.SD_TOKENIZER,
            ModelType.SD,

            ModelType.LLM,
            ModelType.LLM_TOKENIZER,

            ModelType.TTS,
            # ModelType.TTS_DATASET,
            ModelType.TTS_PROCESSOR,
            # ModelType.TTS_FEATURE_EXTRACTOR,
            ModelType.TTS_VOCODER,
            ModelType.TTS_SPEAKER_EMBEDDINGS,
            ModelType.TTS_TOKENIZER,

            ModelType.STT,
            ModelType.STT_PROCESSOR,
            ModelType.STT_FEATURE_EXTRACTOR,
        ]

        self.models = {
            model_type.value: {
                "status": ModelStatus.UNLOADED,
                "path": ""
            } for model_type in model_order
        }

        self.model_column = 0
        self.status_column = 1
        self.load_button_column = 2
        self.unload_button_column = 3
        self.path_column = 4
        self.device_column = 5

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_memory_stats)
        self.timer.start(5000)

        # add items
        self.initialize_model_stats_ui()

    def initialize_model_stats_ui(self):
        # Set row and column count
        headers = ["Model", "Status", "Load", "Unload", "Path", "Device"]
        total_rows = len(self.models.items())
        total_columns = len(headers)
        self.ui.model_stats.setRowCount(total_rows)
        self.ui.model_stats.setColumnCount(total_columns)
        self.ui.model_stats.setHorizontalHeaderLabels(headers)

        # Display model stats for each model
        row = 0
        for model_name, model in self.models.items():
            status: str = str(model["status"].value)
            self.ui.model_stats.setItem(row, self.model_column, QTableWidgetItem(model_name))
            self.ui.model_stats.setItem(row, self.status_column, QTableWidgetItem(status))
            self.ui.model_stats.setItem(row, self.path_column, QTableWidgetItem(model["path"]))
            self.ui.model_stats.setItem(row, self.device_column, QTableWidgetItem(""))

            button = QPushButton("Load")
            button.clicked.connect(partial(self.load_model, model_name))
            self.ui.model_stats.setCellWidget(row, self.load_button_column, button)

            button = QPushButton("Unload")
            button.clicked.connect(partial(self.unload_model, model_name))
            self.ui.model_stats.setCellWidget(row, self.unload_button_column, button)

            self.set_color(row, 1, status)

            row += 1

        # Resize columns and rows
        self.ui.model_stats.resizeColumnsToContents()
        self.ui.model_stats.resizeRowsToContents()
        self.ui.model_stats.horizontalHeader().setStretchLastSection(True)
        for index in range(total_columns):
            self.ui.model_stats.horizontalHeader().setSectionResizeMode(
                index,
                QHeaderView.ResizeMode.ResizeToContents
            )

        # Hide vertical and horizontal headers
        self.ui.model_stats.verticalHeader().setVisible(False)
        self.ui.model_stats.horizontalHeader().setVisible(False)

        self.update_memory_stats()

        QApplication.processEvents()

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
                total_mem = torch.cuda.get_device_properties(device).total_memory / (1024 ** 3)  # Convert bytes to GB
                allocated_mem = torch.cuda.memory_allocated() / (1024 ** 3)  # Convert bytes to GB
                free_mem = total_mem - allocated_mem
                device_name = torch.cuda.get_device_name(device)
            except RuntimeError:
                free_mem = 0
                allocated_mem = 0
                total_mem = 0
                device_name = "N/A"


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

        # Get CPU details
        cpu_memory = psutil.virtual_memory()

        used = cpu_memory.used / (1024.0 ** 3)
        total = cpu_memory.total / (1024.0 ** 3)
        available = cpu_memory.available / (1024.0 ** 3)

        # truncate to 2 decimal places
        used = round(used, 2)
        total = round(total, 2)
        available = round(available, 2)

        self.ui.memory_stats.setItem(row_count - 1, 0, QTableWidgetItem("CPU"))
        self.ui.memory_stats.setItem(row_count - 1, 1, QTableWidgetItem(f"{used}GB"))
        self.ui.memory_stats.setItem(row_count - 1, 2, QTableWidgetItem(f"{total}GB"))
        self.ui.memory_stats.setItem(row_count - 1, 3, QTableWidgetItem(f"{available}GB"))

        # Set colors
        self.ui.memory_stats.item(row_count - 1, 1).setForeground(Qt.red)
        self.ui.memory_stats.item(row_count - 1, 2).setForeground(Qt.yellow)
        self.ui.memory_stats.item(row_count - 1, 3).setForeground(Qt.green)

        QApplication.processEvents()

    @Slot()
    def load_all(self):
        for model in self.models.keys():
            self.load_model(model)

    def load_model(self, model: str):
        if model == ModelType.SD.value:
            self.emit_signal(SignalCode.SD_LOAD_SIGNAL)
        elif model == ModelType.SD_VAE.value:
            self.emit_signal(SignalCode.SD_VAE_LOAD_SIGNAL)
        elif model == ModelType.SD_UNET.value:
            self.emit_signal(SignalCode.SD_UNET_LOAD_SIGNAL)
        elif model == ModelType.SD_TOKENIZER.value:
            self.emit_signal(SignalCode.SD_TOKENIZER_LOAD_SIGNAL)
        elif model == ModelType.SD_TEXT_ENCODER.value:
            self.emit_signal(SignalCode.SD_TEXT_ENCODER_LOAD_SIGNAL)
        elif model == ModelType.SCHEDULER.value:
            self.emit_signal(SignalCode.SCHEDULER_LOAD_SIGNAL)
        elif model == ModelType.TTS.value:
            self.emit_signal(SignalCode.TTS_LOAD_SIGNAL)
        elif model == ModelType.TTS_PROCESSOR.value:
            self.emit_signal(SignalCode.TTS_PROCESSOR_LOAD_SIGNAL)
        # if model == ModelType.TTS_FEATURE_EXTRACTOR.value:
        #     self.emit_signal(SignalCode.TTS_FEATURE_EXTRACTOR_LOAD_SIGNAL)
        elif model == ModelType.TTS_VOCODER.value:
            self.emit_signal(SignalCode.TTS_VOCODER_LOAD_SIGNAL)
        elif model == ModelType.TTS_SPEAKER_EMBEDDINGS.value:
            self.emit_signal(SignalCode.TTS_SPEAKER_EMBEDDINGS_LOAD_SIGNAL)
        elif model == ModelType.TTS_TOKENIZER.value:
            self.emit_signal(SignalCode.TTS_TOKENIZER_LOAD_SIGNAL)
        # if model == ModelType.TTS_DATASET.value:
        #     self.emit_signal(SignalCode.TTS_DATASET_LOAD_SIGNAL)
        elif model == ModelType.STT.value:
            self.emit_signal(SignalCode.STT_LOAD_SIGNAL)
        elif model == ModelType.STT_PROCESSOR.value:
            self.emit_signal(SignalCode.STT_PROCESSOR_LOAD_SIGNAL)
        elif model == ModelType.STT_FEATURE_EXTRACTOR.value:
            self.emit_signal(SignalCode.STT_FEATURE_EXTRACTOR_LOAD_SIGNAL)
        elif model == ModelType.CONTROLNET.value:
            self.emit_signal(SignalCode.CONTROLNET_LOAD_MODEL_SIGNAL)
        elif model == ModelType.CONTROLNET_PROCESSOR.value:
            self.emit_signal(SignalCode.CONTROLNET_PROCESSOR_LOAD_SIGNAL)
        elif model == ModelType.SAFETY_CHECKER.value:
            self.emit_signal(SignalCode.SAFETY_CHECKER_MODEL_LOAD_SIGNAL)
        elif model == ModelType.FEATURE_EXTRACTOR.value:
            self.emit_signal(SignalCode.FEATURE_EXTRACTOR_LOAD_SIGNAL)
        elif model == ModelType.SCHEDULER.value:
            self.emit_signal(SignalCode.SCHEDULER_LOAD_SIGNAL)
        elif model == ModelType.LLM.value:
            self.emit_signal(SignalCode.LLM_LOAD_MODEL_SIGNAL)
        elif model == ModelType.LLM_TOKENIZER.value:
            self.emit_signal(SignalCode.LLM_TOKENIZER_LOAD_SIGNAL)

    @Slot()
    def unload_all(self):
        for model in self.models.keys():
            self.unload_model(model)
        clear_memory()

    def unload_model(self, model: str):
        if model == ModelType.SD.value:
            self.emit_signal(SignalCode.SD_UNLOAD_SIGNAL)
        elif model == ModelType.SD_VAE.value:
            self.emit_signal(SignalCode.SD_VAE_UNLOAD_SIGNAL)
        elif model == ModelType.SD_UNET.value:
            self.emit_signal(SignalCode.SD_UNET_UNLOAD_SIGNAL)
        elif model == ModelType.SD_TOKENIZER.value:
            self.emit_signal(SignalCode.SD_TOKENIZER_UNLOAD_SIGNAL)
        elif model == ModelType.SD_TEXT_ENCODER.value:
            self.emit_signal(SignalCode.SD_TEXT_ENCODER_UNLOAD_SIGNAL)
        elif model == ModelType.SCHEDULER.value:
            self.emit_signal(SignalCode.SCHEDULER_UNLOAD_SIGNAL)
        elif model == ModelType.TTS.value:
            self.emit_signal(SignalCode.TTS_UNLOAD_SIGNAL)
        elif model == ModelType.TTS_PROCESSOR.value:
            self.emit_signal(SignalCode.TTS_PROCESSOR_UNLOAD_SIGNAL)
        # if model == ModelType.TTS_FEATURE_EXTRACTOR.value:
        #     self.emit_signal(SignalCode.TTS_FEATURE_EXTRACTOR_UNLOAD_SIGNAL)
        elif model == ModelType.TTS_VOCODER.value:
            self.emit_signal(SignalCode.TTS_VOCODER_UNLOAD_SIGNAL)
        elif model == ModelType.TTS_SPEAKER_EMBEDDINGS.value:
            self.emit_signal(SignalCode.TTS_SPEAKER_EMBEDDINGS_UNLOAD_SIGNAL)
        elif model == ModelType.TTS_TOKENIZER.value:
            self.emit_signal(SignalCode.TTS_TOKENIZER_UNLOAD_SIGNAL)
        # if model == ModelType.TTS_DATASET.value:
        #     self.emit_signal(SignalCode.TTS_DATASET_UNLOAD_SIGNAL)
        elif model == ModelType.STT.value:
            self.emit_signal(SignalCode.STT_UNLOAD_SIGNAL)
        elif model == ModelType.STT_PROCESSOR.value:
            self.emit_signal(SignalCode.STT_PROCESSOR_UNLOAD_SIGNAL)
        elif model == ModelType.STT_FEATURE_EXTRACTOR.value:
            self.emit_signal(SignalCode.STT_FEATURE_EXTRACTOR_UNLOAD_SIGNAL)
        elif model == ModelType.CONTROLNET.value:
            self.emit_signal(SignalCode.CONTROLNET_UNLOAD_MODEL_SIGNAL)
        elif model == ModelType.CONTROLNET_PROCESSOR.value:
            self.emit_signal(SignalCode.CONTROLNET_PROCESSOR_UNLOAD_SIGNAL)
        elif model == ModelType.SAFETY_CHECKER.value:
            self.emit_signal(SignalCode.SAFETY_CHECKER_MODEL_UNLOAD_SIGNAL)
        elif model == ModelType.FEATURE_EXTRACTOR.value:
            self.emit_signal(SignalCode.FEATURE_EXTRACTOR_UNLOAD_SIGNAL)
        elif model == ModelType.SCHEDULER.value:
            self.emit_signal(SignalCode.SCHEDULER_UNLOAD_SIGNAL)
        elif model == ModelType.LLM.value:
            self.emit_signal(SignalCode.LLM_UNLOAD_MODEL_SIGNAL)
        elif model == ModelType.LLM_TOKENIZER.value:
            self.emit_signal(SignalCode.LLM_TOKENIZER_UNLOAD_SIGNAL)

    def on_model_status_changed_signal(self, data: dict = None):
        self.models[data["model"].value]["status"] = data["status"]
        self.models[data["model"].value]["path"] = data["path"]
        self.update_model_stats_ui(data["model"].value, data["status"], data["path"], data.get("device", ""))

    def update_model_stats_ui(self, model: str, status: ModelStatus, path: str, device: str = ""):
        """
        Iterate through the model stats and update the status of the model
        that matches the model name passed in.
        :param model:
        :param status:
        :param path:
        :return:
        """
        for row in range(self.ui.model_stats.rowCount()):
            item = self.ui.model_stats.item(row, self.model_column)
            if item is None:
                continue
            if item.text() == model:
                self.set_status(row, status, path, device)
                break

    def set_status(self, row: int, status: ModelStatus, path: str = "", device: str = ""):
        """
        Set status of a model in the model stats table.
        :param row:
        :param status:
        :param path:
        :return:
        """
        self.ui.model_stats.item(row, self.status_column).setText(status.value)
        self.ui.model_stats.item(row, self.path_column).setText(path)
        self.ui.model_stats.item(row, self.device_column).setText(device)
        self.set_color(row, self.status_column, status)
        QApplication.processEvents()

    def set_color(self, row, col, status):
        # Set the color of the text according to the status
        if status == ModelStatus.LOADED:
            color = Qt.GlobalColor.green
        elif status == ModelStatus.READY:
            color = Qt.GlobalColor.yellow
        elif status == ModelStatus.LOADING:
            color = Qt.GlobalColor.darkYellow
        elif status == ModelStatus.FAILED:
            color = Qt.GlobalColor.red
        else:
            color = Qt.GlobalColor.lightGray

        try:
            self.ui.model_stats.item(row, col).setForeground(color)
        except AttributeError:
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
