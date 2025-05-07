import threading
import time
import sounddevice as sd
from airunner.gui.widgets.base_widget import BaseWidget
from airunner.gui.widgets.sound_settings.templates.sound_settings_ui import (
    Ui_SoundSettings,
)
from airunner.data.models import SoundSettings
from airunner.enums import SignalCode


class SoundSettingsWidget(BaseWidget):
    widget_class_ = Ui_SoundSettings

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_devices()  # Ensure devices are loaded on initialization
        self.connect_signals()
        self.monitoring = True

    def load_devices(self):
        # Populate comboboxes with available audio devices
        devices = sd.query_devices()
        output_devices = filter(
            None,
            [
                None if device["max_output_channels"] == 0 else device
                for device in devices
            ],
        )
        input_devices = filter(
            None,
            [
                None if device["max_input_channels"] == 0 else device
                for device in devices
            ],
        )

        current_output_device = sd.query_devices(kind="output")
        current_input_device = sd.query_devices(kind="input")

        input_device_names = [device["name"] for device in input_devices]
        output_device_names = [device["name"] for device in output_devices]

        self.ui.playbackComboBox.clear()
        self.ui.playbackComboBox.addItems(output_device_names)
        self.ui.playbackComboBox.setCurrentText(current_output_device["name"])

        self.ui.recordingComboBox.clear()
        self.ui.recordingComboBox.addItems(input_device_names)
        self.ui.recordingComboBox.setCurrentText(current_input_device["name"])

        # Retrieve current settings
        sound_settings = SoundSettings.objects.first()

        # Set playback device
        if (
            sound_settings
            and sound_settings.playback_device in output_device_names
        ):
            self.ui.playbackComboBox.setCurrentText(
                sound_settings.playback_device
            )
        elif output_device_names:
            current_device = output_device_names[0]
            self.ui.playbackComboBox.setCurrentIndex(0)
            sound_settings = SoundSettings.objects.first()
            if sound_settings:
                SoundSettings.objects.update(
                    sound_settings.id, playback_device=current_device
                )

        # Set recording device
        if (
            sound_settings
            and sound_settings.recording_device in input_device_names
        ):
            self.ui.recordingComboBox.setCurrentText(
                sound_settings.recording_device
            )
        elif input_device_names:
            current_device = input_device_names[0]
            self.ui.recordingComboBox.setCurrentIndex(0)
            sound_settings = SoundSettings.objects.first()
            if sound_settings:
                SoundSettings.objects.update(
                    sound_settings.id, recording_device=current_device
                )

    def connect_signals(self):
        self.ui.playbackComboBox.currentTextChanged.connect(
            self.update_playback_device
        )
        self.ui.recordingComboBox.currentTextChanged.connect(
            self.update_recording_device
        )

    def update_playback_device(self, device):
        sound_settings = SoundSettings.objects.first()
        SoundSettings.objects.update(sound_settings.id, playback_device=device)
        self.emit_signal(SignalCode.PLAYBACK_DEVICE_CHANGED, device)

    def update_recording_device(self, device):
        sound_settings = SoundSettings.objects.first()
        SoundSettings.objects.update(
            sound_settings.id, recording_device=device
        )
        self.emit_signal(SignalCode.RECORDING_DEVICE_CHANGED, device)

    def update_microphone_volume(self, volume):
        sound_settings = SoundSettings.objects.first()
        SoundSettings.objects.update(
            sound_settings.id, microphone_volume=volume
        )

    def adjust_input_level(self, value):
        # Adjust the microphone input level
        print(f"Input level adjusted to: {value}")
        # Replace with actual logic to adjust microphone input level
