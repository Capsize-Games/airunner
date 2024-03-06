from airunner.settings import ESPEAK_SETTINGS
from airunner.widgets.base_widget import BaseWidget
from airunner.widgets.tts.templates.espeak_preferences_ui import Ui_espeak_preferences
import pycountry

class EspeakPreferencesWidget(BaseWidget):
    widget_class_ = Ui_espeak_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialize_form()

    def initialize_form(self):
        elements = [
            self.ui.language_combobox,
            self.ui.gender_combobox,
            self.ui.voice_combobox,
        ]

        for element in elements:
            element.blockSignals(True)

        language = self.settings["tts_settings"]["espeak"]["language"]
        gender = self.settings["tts_settings"]["espeak"]["gender"]
        voice = self.settings["tts_settings"]["espeak"]["voice"]
        iso_codes = [country.alpha_2 for country in pycountry.countries]

        self.ui.voice_combobox.clear()
        self.ui.language_combobox.clear()
        self.ui.language_combobox.addItems(iso_codes)
        self.ui.language_combobox.setCurrentText(language)
        self.ui.gender_combobox.clear()
        self.ui.gender_combobox.addItems(["Male", "Female"])
        self.ui.gender_combobox.setCurrentText(gender)
        self.ui.voice_combobox.addItems(ESPEAK_SETTINGS["voices"][gender])
        self.ui.voice_combobox.setCurrentText(voice)

        for element in elements:
            element.blockSignals(False)

        for k in [
            "rate",
            "pitch",
            "volume"
        ]:
            getattr(self.ui, k).settings_loaded(self.callback)

    def callback(self, prop, val):
        settings = self.settings
        settings["tts_settings"]["espeak"][prop] = val
        self.settings = settings

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
        self.ui.voice_combobox.addItems(ESPEAK_SETTINGS["voices"][text])
        settings["tts_settings"]["espeak"]["voice"] = self.ui.voice_combobox.currentText()
        self.settings = settings
