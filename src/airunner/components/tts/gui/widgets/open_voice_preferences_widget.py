import os
import threading

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QFileDialog

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.tts.gui.widgets.templates.open_voice_preferences_ui import (
    Ui_open_voice_preferences,
)
from airunner.components.tts.data.models.openvoice_settings import OpenVoiceSettings
from airunner.enums import AvailableLanguage, TTSModel
from airunner.utils.path_policy import (
    PathPolicyError,
    normalize_local_path,
    resolve_existing_file,
)


_AUDIO_FILE_SUFFIXES = (".wav", ".mp3", ".ogg")


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
            self.ui.voice_sample_path.blockSignals(True)
            self.ui.voice_sample_path.setText(file_path)
            self.ui.voice_sample_path.blockSignals(False)
            self._store_reference_speaker_path(file_path)
            if self._should_precompute_in_background():
                self._start_reference_speaker_precompute(file_path)

    @Slot(str)
    def on_voice_sample_path_textChanged(self, txt: str):
        self._store_reference_speaker_path(txt)

    def _store_reference_speaker_path(self, path: str) -> None:
        """Persist one reference speaker path and notify the app."""
        if not isinstance(path, str) or not path.strip():
            return
        try:
            normalized_path = normalize_local_path(
                path,
                label="Reference speaker path",
            )
        except PathPolicyError as error:
            self.logger.error("Rejected reference speaker path: %s", error)
            return
        if not os.path.isfile(normalized_path):
            return
        try:
            validated_path = resolve_existing_file(
                normalized_path,
                label="Reference speaker path",
                allowed_suffixes=_AUDIO_FILE_SUFFIXES,
            )
        except PathPolicyError as error:
            self.logger.error("Rejected reference speaker path: %s", error)
            return

        open_voice_settings = OpenVoiceSettings.objects.get(self._id)
        if not open_voice_settings:
            return
        if open_voice_settings.reference_speaker_path != validated_path:
            OpenVoiceSettings.objects.update(
                self._id, reference_speaker_path=validated_path
            )
            self._item.reference_speaker_path = validated_path
            self._notify_api_or_app(
                "openvoice_settings",
                "reference_speaker_path",
                validated_path,
            )

    def _should_precompute_in_background(self) -> bool:
        """Return True when no active OpenVoice runtime will warm itself."""
        if not getattr(self.application_settings, "tts_enabled", False):
            return True
        return self.chatbot_voice_model_type != TTSModel.OPENVOICE

    def _start_reference_speaker_precompute(self, file_path: str) -> None:
        """Start one background precompute of the selected voice sample."""
        model_path = getattr(self.path_settings, "tts_model_path", None)
        if not model_path:
            return

        thread = threading.Thread(
            target=self._precompute_reference_speaker,
            args=(file_path, str(model_path)),
            daemon=True,
        )
        thread.start()

    def _precompute_reference_speaker(
        self,
        file_path: str,
        model_path: str,
    ) -> None:
        """Best-effort background precompute for one selected sample."""
        try:
            from airunner.components.tts.managers.openvoice_model_manager import (
                OpenVoiceModelManager,
            )

            OpenVoiceModelManager.precompute_reference_speaker(
                file_path,
                model_path,
            )
        except Exception as error:
            self.logger.error(
                "OpenVoice reference-speaker precompute failed: %s",
                error,
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
