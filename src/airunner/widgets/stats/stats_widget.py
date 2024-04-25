from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem, QHeaderView, QApplication, QPushButton
from airunner.enums import SignalCode, ModelStatus, ModelType
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
            ModelType.CONTROLNET,
            ModelType.CONTROLNET_PROCESSOR,
            ModelType.SCHEDULER,
            ModelType.SD,

            ModelType.LLM,
            ModelType.LLM_TOKENIZER,

            ModelType.TTS,
            ModelType.TTS_DATASET,
            ModelType.TTS_PROCESSOR,
            ModelType.TTS_FEATURE_EXTRACTOR,
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
        self.unload_button_colunm = 3
        self.path_column = 4

        # add items
        self.initialize_model_stats_ui()

    def initialize_model_stats_ui(self):
        # Set row and column count
        total_rows = len(self.models.items())
        total_columns = 5
        self.ui.model_stats.setRowCount(total_rows)
        self.ui.model_stats.setColumnCount(total_columns)
        self.ui.model_stats.setHorizontalHeaderLabels(["Model", "Status", "Load", "Unload", "Path"])

        # Display model stats for each model
        row = 0
        for model_name, model in self.models.items():
            status: str = str(model["status"].value)
            self.ui.model_stats.setItem(row, self.model_column, QTableWidgetItem(model_name))
            self.ui.model_stats.setItem(row, self.status_column, QTableWidgetItem(status))
            self.ui.model_stats.setItem(row, self.path_column, QTableWidgetItem(model["path"]))

            button = QPushButton("Load")
            button.clicked.connect(partial(self.load_model, model_name))
            self.ui.model_stats.setCellWidget(row, self.load_button_column, button)

            button = QPushButton("Unload")
            button.clicked.connect(partial(self.unload_model, model_name))
            self.ui.model_stats.setCellWidget(row, self.unload_button_colunm, button)


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

        QApplication.processEvents()

    def load_model(self, model: str):
        if model == ModelType.LLM.value:
            self.emit_signal(SignalCode.LLM_LOAD_SIGNAL)
        elif model == ModelType.LLM_TOKENIZER.value:
            self.emit_signal(SignalCode.LLM_TOKENIZER_LOAD_SIGNAL)

    def unload_model(self, model: str):
        if model == ModelType.LLM.value:
            self.emit_signal(SignalCode.LLM_UNLOAD_SIGNAL)
        elif model == ModelType.LLM_TOKENIZER.value:
            self.emit_signal(SignalCode.LLM_TOKENIZER_UNLOAD_SIGNAL)

    def on_model_status_changed_signal(self, data: dict = None):
        self.models[data["model"].value]["status"] = data["status"]
        self.models[data["model"].value]["path"] = data["path"]
        self.update_model_stats_ui(data["model"].value, data["status"], data["path"])

    def update_model_stats_ui(self, model: str, status: ModelStatus, path: str):
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
                self.set_status(row, status, path)
                break

    def set_status(self, row: int, status: ModelStatus, path: str = ""):
        """
        Set status of a model in the model stats table.
        :param row:
        :param status:
        :param path:
        :return:
        """
        self.ui.model_stats.item(row, self.status_column).setText(status.value)
        self.ui.model_stats.item(row, self.path_column).setText(path)
        self.set_color(row, self.status_column, status)
        QApplication.processEvents()

    def set_color(self, row, col, status):
        # Set the color of the text according to the status
        if status == ModelStatus.LOADED:
            self.ui.model_stats.item(row, col).setForeground(Qt.GlobalColor.green)
        elif status == ModelStatus.LOADING:
            self.ui.model_stats.item(row, col).setForeground(Qt.GlobalColor.yellow)
        elif status == ModelStatus.FAILED:
            self.ui.model_stats.item(row, col).setForeground(Qt.GlobalColor.red)
        else:
            self.ui.model_stats.item(row, col).setForeground(Qt.GlobalColor.lightGray)

    def on_log_logged_signal(self, data: dict = None):
        """
        Log a message to the console.
        :param data:
        :return:
        """
        self.console_history.append(data["message"])
        self.ui.console.append(data["message"])
        QApplication.processEvents()
