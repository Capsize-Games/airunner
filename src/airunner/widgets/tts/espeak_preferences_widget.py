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
        elements = [
            self.ui.language_combobox,
            self.ui.gender_combobox,
            self.ui.voice_combobox,
        ]

        for element in elements:
            element.blockSignals(True)

        language = self.espeak_settings.language
        gender = self.espeak_settings.gender
        voice = self.espeak_settings.voice
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

        self.ui.rate.init(slider_callback=self.callback, current_value=self.espeak_settings.rate)
        self.ui.volume.init(slider_callback=self.callback, current_value=self.espeak_settings.volume)
        self.ui.pitch.init(slider_callback=self.callback, current_value=self.espeak_settings.pitch)

    def callback(self, attr_name, value, widget=None):
        self.update_espeak_settings(attr_name, value)

    def language_changed(self, text):
        self.update_espeak_settings("language", text)
        self.update_espeak_settings("gender", self.ui.gender_combobox.currentText())
        self.update_espeak_settings("voice", self.ui.voice_combobox.currentText())

        self.update_espeak_settings("language", text)
        self.update_espeak_settings("gender", self.ui.gender_combobox.currentText())
        self.update_espeak_settings("voice", self.ui.voice_combobox.currentText())

    def voice_changed(self, text):
        self.update_espeak_settings("voice", text)

    def gender_changed(self, text):
        self.update_espeak_settings("gender", text)
        self.ui.voice_combobox.clear()
        self.ui.voice_combobox.addItems(ESPEAK_SETTINGS["voices"][text.lower()])
        self.update_espeak_settings("voice", self.ui.voice_combobox.currentText())
