from airunner.enums import SignalCode, TTSModel
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.tts.templates.tts_preferences_ui import (
    Ui_tts_preferences,
)
from airunner.settings import AIRUNNER_ENABLE_OPEN_VOICE


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
                models = [TTSModel.SPEECHT5.value, TTSModel.ESPEAK.value]
                if AIRUNNER_ENABLE_OPEN_VOICE:
                    models.append(TTSModel.OPENVOICE.value)
                self.ui.model_combobox.addItems(models)
                self.ui.model_combobox.setCurrentText(tts_model)

                # Ensure settings are valid before calling _set_model_settings
                if self.chatbot.voice_settings:
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
        self.ui.speecht5_preferences.setVisible(
            tts_model == TTSModel.SPEECHT5.value
        )
        self.ui.espeak_preferences.setVisible(
            tts_model == TTSModel.ESPEAK.value
        )
        if AIRUNNER_ENABLE_OPEN_VOICE:
            self.ui.open_voice_preferences.setVisible(
                tts_model == TTSModel.OPENVOICE.value
            )

    @staticmethod
    def handle_value_change(prop, val):
        pass
