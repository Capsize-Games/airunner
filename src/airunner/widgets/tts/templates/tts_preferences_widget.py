from airunner.settings import VOICES
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.tts.templates.tts_preferences_ui import Ui_tts_preferences
#intfloat/multilingual-e5-large


class TTSPreferencesWidget(BaseWidget):
    widget_class_ = Ui_tts_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voices = VOICES
        self.initialize_form()
    
    def initialize_form(self):
        elements = [
            self.ui.language_combobox,
            self.ui.gender_combobox,
            self.ui.voice_combobox,
            self.ui.use_bark,
            self.ui.enable_tts,
        ]

        for element in elements:
            element.blockSignals(True)

        language = self.settings["tts_settings"]["language"]
        gender = self.settings["tts_settings"]["gender"]
        voice = self.settings["tts_settings"]["voice"]

        self.ui.voice_combobox.clear()
        self.ui.language_combobox.addItems(self.voices.keys())
        self.ui.language_combobox.setCurrentText(language)
        self.ui.gender_combobox.setCurrentText(gender)
        self.ui.voice_combobox.addItems(self.voices[language][gender])
        self.ui.voice_combobox.setCurrentText(voice)
        self.ui.use_bark.setChecked(self.settings["tts_settings"]["use_bark"])
        self.ui.enable_tts.setChecked(self.settings["tts_settings"]["enable_tts"])

        for element in elements:
            element.blockSignals(False)

    def language_changed(self, text):
        settings = self.settings
        settings["tts_settings"]["language"] = text
        settings["tts_settings"]["gender"] = self.ui.gender_combobox.currentText()
        settings["tts_settings"]["voice"] = self.ui.voice_combobox.currentText()
        self.settings = settings

    def voice_changed(self, text):
        settings = self.settings
        settings["tts_settings"]["voice"] = text
        self.settings = settings

    def gender_changed(self, text):
        settings = self.settings
        settings["tts_settings"]["gender"] = text
        settings["tts_settings"]["voice"] = self.ui.voice_combobox.currentText()
        self.settings = settings

    def use_bark_changed(self, val):
        settings = self.settings
        settings["tts_settings"]["use_bark"] = val
        self.settings = settings

    def enable_tts_changed(self, val):
        settings = self.settings
        settings["tts_settings"]["enable_tts"] = val
        self.settings = settings

    def model_changed(self, val):
        settings = self.settings
        settings["tts_settings"]["model"] = val
        settings["tts_settings"]["use_bark"] = val == "Bark"
        print(val)
        print(settings["tts_settings"]["use_bark"])
        self.settings = settings
