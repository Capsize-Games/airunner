from PySide6.QtWidgets import QWidget
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.tts.templates.open_voice_preferences_ui import (
    Ui_open_voice_preferences,
)
from airunner.data.models.openvoice_settings import OpenVoiceSettings


class OpenVoicePreferencesWidget(BaseWidget):
    widget_class_ = Ui_open_voice_preferences

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load_settings(self, settings: OpenVoiceSettings):
        """Load the OpenVoice settings into the widget."""
        self.ui.language_combobox.setCurrentText(settings.language)
        self.ui.speed_slider.setValue(settings.speed)
        self.ui.tone_color_combobox.setCurrentText(settings.tone_color)
        self.ui.pitch_slider.setValue(settings.pitch)
        self.ui.volume_slider.setValue(settings.volume)
        self.ui.voice_combobox.setCurrentText(settings.voice)

    def language_changed(self, text):
        self.update_openvoice_settings("language", text)

    def speed_changed(self, value):
        self.update_openvoice_settings("speed", value)

    def tone_color_changed(self, text):
        self.update_openvoice_settings("tone_color", text)

    def pitch_changed(self, value):
        self.update_openvoice_settings("pitch", value)

    def volume_changed(self, value):
        self.update_openvoice_settings("volume", value)

    def voice_changed(self, text):
        self.update_openvoice_settings("voice", text)
