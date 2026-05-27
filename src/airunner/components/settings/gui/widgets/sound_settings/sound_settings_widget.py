from importlib import import_module

from PySide6.QtCore import Slot
from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.settings.gui.widgets.sound_settings.templates.sound_settings_ui import (
    Ui_SoundSettings,
)
from airunner.enums import SignalCode


def _sounddevice():
    return import_module("sounddevice")


class SoundSettingsWidget(BaseWidget):
    widget_class_ = Ui_SoundSettings

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_devices()  # Ensure devices are loaded on initialization
        self.monitoring = True

    def load_devices(self):
        # Populate comboboxes with available audio devices
        sd = _sounddevice()
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

        current_output_device = None
        current_input_device = None

        try:
            current_output_device = sd.query_devices(kind="output")
        except sd.PortAudioError as e:
            self.logger.error(
                f"PortAudioError: Unable to query output devices. {e}"
            )

        try:
            current_input_device = sd.query_devices(kind="input")
        except sd.PortAudioError as e:
            self.logger.error(
                f"PortAudioError: Unable to query input devices. {e}"
            )

        input_device_names = [device["name"] for device in input_devices]
        output_device_names = [device["name"] for device in output_devices]

        self.ui.playbackComboBox.clear()
        self.ui.playbackComboBox.addItems(output_device_names)

        # Set current device only if successfully queried
        if current_output_device is not None and output_device_names:
            self.ui.playbackComboBox.setCurrentText(
                current_output_device["name"]
            )

        self.ui.recordingComboBox.clear()
        self.ui.recordingComboBox.addItems(input_device_names)

        # Set current device only if successfully queried
        if current_input_device is not None and input_device_names:
            self.ui.recordingComboBox.setCurrentText(
                current_input_device["name"]
            )

        sound_settings = self.resource_store.get_singleton("SoundSettings")

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
            self.resource_store.update_singleton(
                "SoundSettings",
                {"playback_device": current_device},
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
            self.resource_store.update_singleton(
                "SoundSettings",
                {"recording_device": current_device},
            )

    @Slot(str)
    def on_playbackComboBox_currentTextChanged(self, device: str):
        self.resource_store.update_singleton(
            "SoundSettings",
            {"playback_device": device},
        )
        self.emit_signal(SignalCode.PLAYBACK_DEVICE_CHANGED, device)

    @Slot(str)
    def on_recordingComboBox_currentTextChanged(self, device: str):
        self.resource_store.update_singleton(
            "SoundSettings",
            {"recording_device": device},
        )
        self.emit_signal(SignalCode.RECORDING_DEVICE_CHANGED, device)

    def update_microphone_volume(self, volume):
        self.resource_store.update_singleton(
            "SoundSettings",
            {"microphone_volume": volume},
        )

    def adjust_input_level(self, value):
        # Adjust the microphone input level
        print(f"Input level adjusted to: {value}")
        # Replace with actual logic to adjust microphone input level
