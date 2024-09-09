import pyttsx3

from airunner.settings import ESPEAK_SETTINGS
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.tts.templates.espeak_preferences_ui import Ui_espeak_preferences
import pycountry

class ESpeakPreferencesWidget(BaseWidget):
    widget_class_ = Ui_espeak_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize_form(self):
        settings = self.settings
        elements = [
            self.ui.language_combobox,
            self.ui.gender_combobox,
            self.ui.voice_combobox,
        ]

        for element in elements:
            element.blockSignals(True)

        language = settings["tts_settings"]["espeak"]["language"]
        gender = settings["tts_settings"]["espeak"]["gender"]
        voice = settings["tts_settings"]["espeak"]["voice"]
        iso_codes = [country.alpha_2 for country in pycountry.countries]

        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        voice_names = [voice.name for voice in voices]

        self.ui.language_combobox.clear()
        self.ui.language_combobox.addItems(iso_codes)
        self.ui.language_combobox.setCurrentText(language)
        self.ui.gender_combobox.clear()
        self.ui.gender_combobox.addItems(["Male", "Female"])
        self.ui.gender_combobox.setCurrentText(gender)
        self.ui.voice_combobox.clear()
        self.ui.voice_combobox.addItems(voice_names)
        self.ui.voice_combobox.setCurrentText(voice)

        for element in elements:
            element.blockSignals(False)

    def language_changed(self, text):
        settings = self.settings
        settings["tts_settings"]["espeak"]["language"] = text
        settings["tts_settings"]["espeak"]["gender"] = self.ui.gender_combobox.currentText()
        settings["tts_settings"]["espeak"]["voice"] = self.ui.voice_combobox.currentText()
        self.settings = settings

    def voice_changed(self, text):
        settings = self.settings
        settings["tts_settings"]["espeak"]["voice"] = text
        self.settings = settings

    def gender_changed(self, text):
        settings = self.settings
        settings["tts_settings"]["espeak"]["gender"] = text
        self.ui.voice_combobox.clear()
        self.ui.voice_combobox.addItems(ESPEAK_SETTINGS["voices"][text.lower()])
        settings["tts_settings"]["espeak"]["voice"] = self.ui.voice_combobox.currentText()
        self.settings = settings
