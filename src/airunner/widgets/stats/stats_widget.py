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
        self.register(SignalCode.SAFETY_CHECKER_LOADED_SIGNAL, self.on_safety_checker_loaded)
        self.register(SignalCode.SAFETY_CHECKER_UNLOADED_SIGNAL, self.on_safety_checker_unloaded)
        self.register(SignalCode.SAFETY_CHECKER_FAILED_SIGNAL, self.on_safety_checker_failed)

        self.register(SignalCode.FEATURE_EXTRACTOR_LOADED_SIGNAL, self.on_feature_extractor_loaded)
        self.register(SignalCode.FEATURE_EXTRACTOR_UNLOADED_SIGNAL, self.on_feature_extractor_unloaded)
        self.register(SignalCode.FEATURE_EXTRACTOR_FAILED_SIGNAL, self.on_feature_extractor_failed)

        self.register(SignalCode.STABLE_DIFFUSION_LOADED_SIGNAL, self.on_stable_diffusion_loaded)
        self.register(SignalCode.STABLE_DIFFUSION_UNLOADED_SIGNAL, self.on_stable_diffusion_unloaded)
        self.register(SignalCode.STABLE_DIFFUSION_FAILED_SIGNAL, self.on_stable_diffusion_failed)

        self.register(SignalCode.CONTROLNET_LOADED_SIGNAL, self.on_controlnet_loaded)
        self.register(SignalCode.CONTROLNET_LOADING_SIGNAL, self.on_controlnet_loading)
        self.register(SignalCode.CONTROLNET_UNLOADED_SIGNAL, self.on_controlnet_unloaded)
        self.register(SignalCode.CONTROLNET_FAILED_SIGNAL, self.on_controlnet_failed)

        self.register(SignalCode.TTS_MODEL_LOADED_SIGNAL, self.on_tts_model_loaded)
        self.register(SignalCode.TTS_MODEL_UNLOADED_SIGNAL, self.on_tts_model_unloaded)
        self.register(SignalCode.TTS_MODEL_FAILED_SIGNAL, self.on_tts_model_failed)

        self.register(SignalCode.TTS_PROCESSOR_LOADED_SIGNAL, self.on_tts_processor_loaded)
        self.register(SignalCode.TTS_PROCESSOR_UNLOADED_SIGNAL, self.on_tts_processor_unloaded)
        self.register(SignalCode.TTS_PROCESSOR_FAILED_SIGNAL, self.on_tts_processor_failed)

        self.register(SignalCode.TTS_FEATURE_EXTRACTOR_LOADED_SIGNAL, self.on_tts_feature_extractor_loaded)
        self.register(SignalCode.TTS_FEATURE_EXTRACTOR_UNLOADED_SIGNAL, self.on_tts_feature_extractor_unloaded)
        self.register(SignalCode.TTS_FEATURE_EXTRACTOR_FAILED_SIGNAL, self.on_tts_feature_extractor_failed)

        self.register(SignalCode.STT_MODEL_LOADED_SIGNAL, self.on_stt_model_loaded)
        self.register(SignalCode.STT_MODEL_UNLOADED_SIGNAL, self.on_stt_model_unloaded)
        self.register(SignalCode.STT_MODEL_FAILED_SIGNAL, self.on_stt_model_failed)

        self.register(SignalCode.STT_PROCESSOR_LOADED_SIGNAL, self.on_stt_processor_loaded)
        self.register(SignalCode.STT_PROCESSOR_UNLOADED_SIGNAL, self.on_stt_processor_unloaded)
        self.register(SignalCode.STT_PROCESSOR_FAILED_SIGNAL, self.on_stt_processor_failed)

        self.register(SignalCode.STT_VOCODER_LOADED_SIGNAL, self.on_stt_vocoder_loaded)
        self.register(SignalCode.STT_VOCODER_UNLOADED_SIGNAL, self.on_stt_vocoder_unloaded)
        self.register(SignalCode.STT_VOCODER_FAILED_SIGNAL, self.on_stt_vocoder_failed)

        self.register(SignalCode.STT_SPEAKER_EMBEDDINGS_LOADED_SIGNAL, self.on_stt_embeddings_loaded)
        self.register(SignalCode.STT_SPEAKER_EMBEDDINGS_UNLOADED_SIGNAL, self.on_stt_embeddings_unloaded)
        self.register(SignalCode.STT_SPEAKER_EMBEDDINGS_FAILED_SIGNAL, self.on_stt_embeddings_failed)

        self.register(SignalCode.LOAD_SAFETY_CHECKER_SIGNAL, self.on_load_safety_checker)
        self.register(SignalCode.SD_LOAD_SIGNAL, self.on_load_safety_checker)

        self.register(SignalCode.LOG_LOGGED_SIGNAL, self.on_log_logged)
        # add items
        self.initialize_model_stats_ui()
        self.initialize_module_stats_ui()

        self.safety_checker_model_status = ModelStatus.UNLOADED

    def initialize_model_stats_ui(self):
        self.ui.model_stats.setRowCount(11)
        self.ui.model_stats.setColumnCount(3)
        self.ui.model_stats.setHorizontalHeaderLabels(["Model", "Status", "Actions", "Size"])

        # Model Name
        self.ui.model_stats.setItem(0, 0, QTableWidgetItem("SD Safety Checker"))
        self.ui.model_stats.setItem(1, 0, QTableWidgetItem("SD Feature Extractor"))
        self.ui.model_stats.setItem(2, 0, QTableWidgetItem("SD Model"))
        self.ui.model_stats.setItem(3, 0, QTableWidgetItem("SD Controlnet"))
        self.ui.model_stats.setItem(4, 0, QTableWidgetItem("TTS Model"))
        self.ui.model_stats.setItem(5, 0, QTableWidgetItem("TTS Processor"))
        self.ui.model_stats.setItem(6, 0, QTableWidgetItem("TTS Feature Extractor"))
        self.ui.model_stats.setItem(7, 0, QTableWidgetItem("STT Model"))
        self.ui.model_stats.setItem(8, 0, QTableWidgetItem("STT Processor"))
        self.ui.model_stats.setItem(9, 0, QTableWidgetItem("STT Vocoder"))
        self.ui.model_stats.setItem(10, 0, QTableWidgetItem("STT Embeddings"))

        for n in range(11):
            self.ui.model_stats.setItem(n, 1, QTableWidgetItem(ModelStatus.UNLOADED.value))
            self.ui.model_stats.setItem(n, 2, QTableWidgetItem(""))

        self.ui.model_stats.resizeColumnsToContents()
        self.ui.model_stats.resizeRowsToContents()

        self.ui.model_stats.horizontalHeader().setStretchLastSection(True)
        self.ui.model_stats.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.ui.model_stats.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.ui.model_stats.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.ui.model_stats.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        # Hide vertical and horizontal headers
        self.ui.model_stats.verticalHeader().setVisible(False)
        self.ui.model_stats.horizontalHeader().setVisible(False)

    def initialize_module_stats_ui(self):
        pass

    def on_safety_checker_loaded(self, data=None):
        self.safety_checker_model_status = ModelStatus.LOADED
        self.update_safety_checker_model_status(data["path"])

    def on_safety_checker_unloaded(self, data=None):
        if self.safety_checker_model_status is not ModelStatus.UNLOADED:
            self.safety_checker_model_status = ModelStatus.UNLOADED
            self.update_safety_checker_model_status("")

    def on_safety_checker_failed(self, data=None):
        self.safety_checker_model_status = ModelStatus.FAILED
        self.update_safety_checker_model_status(data["path"])

    def on_load_safety_checker(self, data=None):
        if self.safety_checker_model_status is not ModelStatus.LOADING:
            self.safety_checker_model_status = ModelStatus.LOADING
            self.update_safety_checker_model_status("")

    def on_log_logged(self, data=None):
        self.ui.console.append(str(data["message"]))

    def update_safety_checker_model_status(self, path: str):
        self.ui.model_stats.item(0, 1).setText(self.safety_checker_model_status.value)
        self.ui.model_stats.item(0, 2).setText(path)
        QApplication.processEvents()

    def on_feature_extractor_loaded(self, data=None):
        self.ui.model_stats.item(1, 1).setText(ModelStatus.LOADED.value)
        self.ui.model_stats.item(1, 2).setText(data["path"])

    def on_feature_extractor_unloaded(self, data=None):
        self.ui.model_stats.item(1, 1).setText(ModelStatus.UNLOADED.value)
        self.ui.model_stats.item(1, 2).setText("")

    def on_feature_extractor_failed(self, data=None):
        self.ui.model_stats.item(1, 1).setText(ModelStatus.FAILED.value)
        self.ui.model_stats.item(1, 2).setText(data["path"])

    def on_stable_diffusion_loaded(self, data=None):
        self.ui.model_stats.item(2, 1).setText(ModelStatus.LOADED.value)
        self.ui.model_stats.item(2, 2).setText(data["path"])

    def on_stable_diffusion_unloaded(self, data=None):
        self.ui.model_stats.item(2, 1).setText(ModelStatus.UNLOADED.value)
        self.ui.model_stats.item(2, 2).setText("")

    def on_stable_diffusion_failed(self, data=None):
        self.ui.model_stats.item(2, 1).setText(ModelStatus.FAILED.value)
        self.ui.model_stats.item(2, 2).setText(data["path"])

    def on_controlnet_loaded(self, data=None):
        self.ui.model_stats.item(3, 1).setText(ModelStatus.LOADED.value)
        self.ui.model_stats.item(3, 2).setText(data["path"])

    def on_controlnet_loading(self, data=None):
        self.ui.model_stats.item(3, 1).setText(ModelStatus.LOADING.value)
        self.ui.model_stats.item(3, 2).setText(data["path"])
        QApplication.processEvents()

    def on_controlnet_unloaded(self, data=None):
        self.ui.model_stats.item(3, 1).setText(ModelStatus.UNLOADED.value)
        self.ui.model_stats.item(3, 2).setText("")

    def on_controlnet_failed(self, data=None):
        self.ui.model_stats.item(3, 1).setText(ModelStatus.FAILED.value)
        self.ui.model_stats.item(3, 2).setText(data["path"])

    def on_tts_model_loaded(self, data=None):
        self.ui.model_stats.item(4, 1).setText(ModelStatus.LOADED.value)
        self.ui.model_stats.item(4, 2).setText(data["path"])

    def on_tts_model_unloaded(self, data=None):
        self.ui.model_stats.item(4, 1).setText(ModelStatus.UNLOADED.value)
        self.ui.model_stats.item(4, 2).setText("")

    def on_tts_model_failed(self, data=None):
        self.ui.model_stats.item(4, 1).setText(ModelStatus.FAILED.value)
        self.ui.model_stats.item(4, 2).setText(data["path"])

    def on_tts_processor_loaded(self, data=None):
        self.ui.model_stats.item(5, 1).setText(ModelStatus.LOADED.value)
        self.ui.model_stats.item(5, 2).setText(data["path"])

    def on_tts_processor_unloaded(self, data=None):
        self.ui.model_stats.item(5, 1).setText(ModelStatus.UNLOADED.value)
        self.ui.model_stats.item(5, 2).setText("")

    def on_tts_processor_failed(self, data=None):
        self.ui.model_stats.item(5, 1).setText(ModelStatus.FAILED.value)
        self.ui.model_stats.item(5, 2).setText(data["path"])


    def on_tts_feature_extractor_loaded(self, data=None):
        self.ui.model_stats.item(6, 1).setText(ModelStatus.LOADED.value)
        self.ui.model_stats.item(6, 2).setText(data["path"])

    def on_tts_feature_extractor_unloaded(self, data=None):
        self.ui.model_stats.item(6, 1).setText(ModelStatus.UNLOADED.value)
        self.ui.model_stats.item(6, 2).setText("")

    def on_tts_feature_extractor_failed(self, data=None):
        self.ui.model_stats.item(6, 1).setText(ModelStatus.FAILED.value)
        self.ui.model_stats.item(6, 2).setText(data["path"])

    def on_stt_model_loaded(self, data=None):
        self.ui.model_stats.item(7, 1).setText(ModelStatus.LOADED.value)
        self.ui.model_stats.item(7, 2).setText(data["path"])

    def on_stt_model_unloaded(self, data=None):
        self.ui.model_stats.item(7, 1).setText(ModelStatus.UNLOADED.value)
        self.ui.model_stats.item(7, 2).setText("")

    def on_stt_model_failed(self, data=None):
        self.ui.model_stats.item(7, 1).setText(ModelStatus.FAILED.value)
        self.ui.model_stats.item(7, 2).setText(data["path"])

    def on_stt_processor_loaded(self, data=None):
        self.ui.model_stats.item(8, 1).setText(ModelStatus.LOADED.value)
        self.ui.model_stats.item(8, 2).setText(data["path"])

    def on_stt_processor_unloaded(self, data=None):
        self.ui.model_stats.item(8, 1).setText(ModelStatus.UNLOADED.value)
        self.ui.model_stats.item(8, 2).setText("")

    def on_stt_processor_failed(self, data=None):
        self.ui.model_stats.item(8, 1).setText(ModelStatus.FAILED.value)
        self.ui.model_stats.item(8, 2).setText(data["path"])

    def on_stt_vocoder_loaded(self, data=None):
        self.ui.model_stats.item(9, 1).setText(ModelStatus.LOADED.value)
        self.ui.model_stats.item(9, 2).setText(data["path"])

    def on_stt_vocoder_unloaded(self, data=None):
        self.ui.model_stats.item(9, 1).setText(ModelStatus.UNLOADED.value)
        self.ui.model_stats.item(9, 2).setText("")

    def on_stt_vocoder_failed(self, data=None):
        self.ui.model_stats.item(9, 1).setText(ModelStatus.FAILED.value)
        self.ui.model_stats.item(9, 2).setText(data["path"])

    def on_stt_embeddings_loaded(self, data=None):
        self.ui.model_stats.item(10, 1).setText(ModelStatus.LOADED.value)
        self.ui.model_stats.item(10, 2).setText(data["path"])

    def on_stt_embeddings_unloaded(self, data=None):
        self.ui.model_stats.item(10, 1).setText(ModelStatus.UNLOADED.value)
        self.ui.model_stats.item(10, 2).setText("")

    def on_stt_embeddings_failed(self, data=None):
        self.ui.model_stats.item(10, 1).setText(ModelStatus.FAILED.value)
        self.ui.model_stats.item(10, 2).setText(data["path"])
