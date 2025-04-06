import pyttsx3
from PySide6.QtWidgets import QWidget

from airunner.data.bootstrap.espeak_settings_data import ESPEAK_SETTINGS_DATA
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.tts.templates.espeak_preferences_ui import (
    Ui_espeak_preferences,
)
import pycountry
from airunner.data.models.espeak_settings import EspeakSettings


class EspeakPreferencesWidget(BaseWidget):
    widget_class_ = Ui_espeak_preferences

    def __init__(self, id: int, *args, **kwargs):
        self._id: int = id
        self._item: EspeakSettings = EspeakSettings.objects.get(self._id)
        if not self._item:
            self._item = EspeakSettings.objects.create()
        super().__init__(*args, **kwargs)

    def initialize_ui(self):
        self.ui.pitch.setProperty("table_item", self._item)
        self.ui.rate.setProperty("table_item", self._item)
        self.ui.volume.setProperty("table_item", self._item)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_settings()

    def initialize_form(self):
        settings = EspeakSettings.objects.get(self._id)
        if settings is None:
            print(f"Settings not found for ID: {self._id}")
            return

        # Ensure required attributes exist in settings
        if not all(
            hasattr(settings, attr) for attr in ["rate", "volume", "pitch"]
        ):
            print(f"Missing attributes in settings for ID: {self._id}")
            return

        elements = [
            self.ui.language_combobox,
            self.ui.gender_combobox,
            self.ui.voice_combobox,
        ]

        for element in elements:
            element.blockSignals(True)

        language = settings.language
        gender = settings.gender
        voice = settings.voice
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

        self.ui.rate.init(
            slider_callback=self.callback,
            current_value=settings.rate,
        )
        self.ui.volume.init(
            slider_callback=self.callback,
            current_value=settings.volume,
        )
        self.ui.pitch.init(
            slider_callback=self.callback,
            current_value=settings.pitch,
        )

    def callback(self, attr_name, value, _widget=None):
        self.update_espeak_settings(attr_name, value)

    def language_changed(self, text):
        self.update_espeak_settings("language", text)
        self.update_espeak_settings(
            "gender", self.ui.gender_combobox.currentText()
        )
        self.update_espeak_settings(
            "voice", self.ui.voice_combobox.currentText()
        )

        self.update_espeak_settings("language", text)
        self.update_espeak_settings(
            "gender", self.ui.gender_combobox.currentText()
        )
        self.update_espeak_settings(
            "voice", self.ui.voice_combobox.currentText()
        )
      
    def voice_changed(self, text):
        self.update_espeak_settings("voice", text)

    def gender_changed(self, text):
        self.update_espeak_settings("gender", text)
        self.ui.voice_combobox.clear()
        self.ui.voice_combobox.addItems(ESPEAK_SETTINGS_DATA["voices"][text])
        self.update_espeak_settings(
            "voice", self.ui.voice_combobox.currentText()
        )

    def load_settings(self):
        """Load the Espeak settings into the widget."""
        # Populate the widget with settings (e.g., rate, pitch, volume)
        pass
