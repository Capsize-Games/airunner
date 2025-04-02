from airunner.enums import SignalCode
from airunner.gui.widgets.base_widget import BaseWidget
from PySide6.QtWidgets import (
    QInputDialog,
    QPushButton,
    QVBoxLayout,
    QLineEdit,
    QComboBox,
    QWidget,
    QMessageBox,
)
from airunner.gui.widgets.tts.templates.tts_preferences_ui import (
    Ui_tts_preferences,
)


class TTSPreferencesWidget(BaseWidget):
    widget_class_ = Ui_tts_preferences

    def initialize_form(self):
        elements = [
            self.ui.enable_tts,
            self.ui.model_combobox,
        ]

        for element in elements:
            element.blockSignals(True)

        if self._tts_settings:
            tts_model = (
                self.chatbot.voice_settings.model_type
                if self.chatbot.voice_settings
                else None
            )
            if tts_model:
                self.ui.enable_tts.setChecked(
                    self.application_settings.tts_enabled
                )
                self.ui.model_combobox.clear()
                models = ["SpeechT5", "Espeak"]
                self.ui.model_combobox.addItems(models)
                self.ui.model_combobox.setCurrentText(tts_model)
                self._set_model_settings(tts_model)

        for element in elements:
            element.blockSignals(False)

    def enable_tts_changed(self, val):
        self.update_tts_settings("tts_enabled", val)

    def model_changed(self, val):
        self.update_tts_settings("model", val)
        self._set_model_settings(val)
        self.emit_signal(SignalCode.TTS_MODEL_CHANGED, {"model": val})

    def _set_model_settings(self, tts_model):
        self.ui.speecht5_preferences.setVisible(tts_model == "SpeechT5")
        self.ui.espeak_preferences.setVisible(tts_model == "Espeak")

    @staticmethod
    def handle_value_change(prop, val):
        print(prop, val)
