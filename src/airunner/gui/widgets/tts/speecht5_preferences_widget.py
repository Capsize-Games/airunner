from PySide6.QtWidgets import QWidget
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.tts.templates.speecht5_preferences_ui import (
    Ui_speecht5_preferences,
)
from airunner.data.models.speech_t5_settings import SpeechT5Settings


class SpeechT5PreferencesWidget(BaseWidget):
    widget_class_ = Ui_speecht5_preferences

    def __init__(self, id: int, *args, **kwargs):
        self._id: int = id
        self._item: SpeechT5Settings = SpeechT5Settings.objects.get(self._id)
        if not self._item:
            self._item = SpeechT5Settings.objects.create()
        super().__init__(*args, **kwargs)

    def initialize_ui(self):
        self.ui.pitch.setProperty("table_item", self._item)
        voice = None

        settings = SpeechT5Settings.objects.get(self._id)

        if settings is not None:
            voice = settings.voice

        if voice:
            self.ui.voice.setCurrentText(voice)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_settings()

    def initialize_form(self):
        settings = SpeechT5Settings.objects.get(self._id)
        if settings is not None:
            self.ui.pitch.init(current_value=settings.pitch / 100)

    def voice_changed(self, text):
        self.update_speech_t5_settings("voice", text)

    def load_settings(self):
        """Load the SpeechT5 settings into the widget."""
        # Populate the widget with settings (e.g., pitch, voice)
        pass
