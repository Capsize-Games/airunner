from PySide6.QtCore import Slot
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.tts.templates.open_voice_preferences_ui import (
    Ui_open_voice_preferences,
)
from airunner.data.models.openvoice_settings import OpenVoiceSettings
from airunner.enums import AvailableLanguage


class OpenVoicePreferencesWidget(BaseWidget):
    widget_class_ = Ui_open_voice_preferences

    def __init__(self, id: int, *args, **kwargs):
        self._id: int = id
        super().__init__(*args, **kwargs)

        # initialize comboboxes
        self.ui.language_combobox.addItems(
            [lang.value for lang in AvailableLanguage]
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.load_settings()

    def load_settings(self):
        """Load the OpenVoice settings into the widget."""
        settings = OpenVoiceSettings.objects.get(self._id)
        if not settings:
            return
        self.ui.language_combobox.setCurrentText(settings.language)
        self.ui.speed_slider.setValue(settings.speed)

    @Slot(str)
    def language_changed(self, text):
        OpenVoiceSettings.objects.update(self._id, language=text)

    @Slot(int)
    def speed_changed(self, value):
        OpenVoiceSettings.objects.update(self._id, speed=value)
