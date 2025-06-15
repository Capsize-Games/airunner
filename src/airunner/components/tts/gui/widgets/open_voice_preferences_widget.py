from PySide6.QtCore import Slot
from PySide6.QtWidgets import QFileDialog

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.tts.gui.widgets.templates.open_voice_preferences_ui import (
    Ui_open_voice_preferences,
)
from airunner.components.tts.data.models.openvoice_settings import OpenVoiceSettings
from airunner.enums import AvailableLanguage


class OpenVoicePreferencesWidget(BaseWidget):
    widget_class_ = Ui_open_voice_preferences

    def __init__(self, id: int, *args, **kwargs):
        self._id: int = id
        self._item: OpenVoiceSettings = OpenVoiceSettings.objects.get(self._id)
        if not self._item:
            self._item = OpenVoiceSettings.objects.create()
        super().__init__(*args, **kwargs)
        self.ui.voice_sample_path.setText(self._item.reference_speaker_path)

    @Slot()
    def on_browse_voice_sample_path_button_clicked(self):
        """Open a file dialog to select a voice sample path."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select Voice Sample Path"),
            "",
            self.tr("Audio Files (*.wav *.mp3 *.ogg);;All Files (*)"),
        )
        if file_path:
            self.ui.voice_sample_path.setText(file_path)
            open_voice_settings = OpenVoiceSettings.objects.get(self._id)
            if not open_voice_settings:
                return
            OpenVoiceSettings.objects.update(
                self._id, reference_speaker_path=file_path
            )

    @Slot(str)
    def on_voice_sample_path_textChanged(self, txt: str):
        open_voice_settings = OpenVoiceSettings.objects.get(self._id)
        if not open_voice_settings:
            return
        if open_voice_settings.reference_speaker_path != txt:
            OpenVoiceSettings.objects.update(
                self._id, reference_speaker_path=txt
            )

    def initialize_ui(self):
        # initialize comboboxes
        self.ui.language_combobox.addItems(
            [lang.value for lang in AvailableLanguage]
        )

        # Set the default language to the first item in the combobox
        self.ui.speed_slider.setProperty("table_item", self._item)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_settings()

    def load_settings(self):
        """Load the OpenVoice settings into the widget."""
        settings = OpenVoiceSettings.objects.get(self._id)
        if not settings:
            return
        self.ui.language_combobox.setCurrentText(settings.language)

    @Slot(str)
    def language_changed(self, text):
        OpenVoiceSettings.objects.update(self._id, language=text)

    @Slot(int)
    def speed_changed(self, value):
        OpenVoiceSettings.objects.update(self._id, speed=value)
