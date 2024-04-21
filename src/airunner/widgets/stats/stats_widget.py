from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem, QHeaderView, QApplication
from airunner.enums import SignalCode, ModelStatus
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

        self.models = {
            "SD Safety Checker": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "SD Feature Extractor": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "SD Controlnet": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "SD Model": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "SD Controlnet Processor": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "SD Scheduler": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "TTS Model": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "TTS Processor": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "TTS Feature Extractor": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "TTS Vocoder": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "TTS Speaker Embeddings": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "TTS Tokenizer": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "STT Model": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "STT Processor": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
            "STT Feature Extractor": {
                "status": ModelStatus.UNLOADED,
                "path": ""
            },
        }

        # add items
        self.initialize_model_stats_ui()

    def initialize_model_stats_ui(self):
        # Set row and column count
        total_rows = len(self.models.items())
        total_columns = 3
        self.ui.model_stats.setRowCount(total_rows)
        self.ui.model_stats.setColumnCount(total_columns)
        self.ui.model_stats.setHorizontalHeaderLabels(["Model", "Status", "Path"])

        # Display model stats for each model
        row = 0
        for model_name, model in self.models.items():
            status: str = str(model["status"].value)
            self.ui.model_stats.setItem(row, 0, QTableWidgetItem(model_name))
            self.ui.model_stats.setItem(row, 1, QTableWidgetItem(status))
            self.ui.model_stats.setItem(row, 2, QTableWidgetItem(model["path"]))

            self.set_color(row, 1, status)

            row += 1

        # Resize columns and rows
        self.ui.model_stats.resizeColumnsToContents()
        self.ui.model_stats.resizeRowsToContents()
        self.ui.model_stats.horizontalHeader().setStretchLastSection(True)
        for n in range(total_columns):
            self.ui.model_stats.horizontalHeader().setSectionResizeMode(n, QHeaderView.ResizeMode.ResizeToContents)

        # Hide vertical and horizontal headers
        self.ui.model_stats.verticalHeader().setVisible(False)
        self.ui.model_stats.horizontalHeader().setVisible(False)

        QApplication.processEvents()

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
            item = self.ui.model_stats.item(row, 0)
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
        self.ui.model_stats.item(row, 1).setText(status.value)
        self.ui.model_stats.item(row, 2).setText(path)

        self.set_color(row, 1, status)

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