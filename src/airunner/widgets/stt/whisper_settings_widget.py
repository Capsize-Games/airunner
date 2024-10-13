from PySide6.QtCore import Slot

from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.stt.templates.whisper_settings_ui import Ui_whisper_settings


class WhisperSettingsWidget(BaseWidget):
    widget_class_ = Ui_whisper_settings

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui.language.blockSignals(True)
        self.ui.task.blockSignals(True)
        self.ui.is_multilingual.blockSignals(True)
        self.ui.language.addItems(["en", "es", "fr", "de", "it", "nl", "pl", "pt", "ru", "zh"])
        self.ui.language.setCurrentText(self.whisper_settings.language)
        self.ui.is_multilingual.setChecked(self.whisper_settings.is_multilingual)
        self.ui.task.addItems(["transcribe", "translate"])
        self.ui.task.setCurrentText(self.whisper_settings.task)
        self.ui.is_multilingual.blockSignals(False)
        self.ui.task.blockSignals(False)
        self.ui.language.blockSignals(False)

    @Slot(bool)
    def is_multilingual_changed(self, bool):
        self.update_settings_by_name("whisper_settings", "is_multilingual", bool)

    @Slot(str)
    def on_language_changed(self, language):
        self.update_settings_by_name("whisper_settings", "language", language)

    @Slot(int)
    def on_task_changed(self, value):
        self.update_settings_by_name("whisper_settings", "task", value)

    @Slot()
    def on_reset_default_clicked(self):
        self.ui.language.setCurrentText("en")
        self.ui.is_multilingual.setChecked(False)
        self.ui.task.setCurrentIndex(0)
        self.ui.temperature.setValue(800)
        self.ui.compression_ratio_threshold_slider.setValue(1.35)
        self.ui.logprob_threshold_slider.setValue(-1.0)
        self.ui.no_speech_threshold_slider.setValue(0.2)
        self.ui.time_precision_slider.setValue(0.02)
