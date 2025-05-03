import sounddevice as sd
from typing import Optional, Dict, Any
import logging


class SoundDeviceManager:
    """
    Central manager for audio input and output streams using sounddevice.
    Handles initialization, management, and cleanup of audio streams.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._in_stream = None
        self._out_stream = None
        self._selected_input_device = None
        self._selected_output_device = None

    @property
    def in_stream(self):
        return self._in_stream

    @property
    def out_stream(self):
        return self._out_stream

    def get_devices(self) -> Dict:
        """Get all available audio devices."""
        return sd.query_devices()

    def get_input_device_index(self, device_name: str) -> Optional[int]:
        """Get the index of an input device by name."""
        return self._get_device_index(device_name, kind="input")

    def get_output_device_index(self, device_name: str) -> Optional[int]:
        """Get the index of an output device by name."""
        return self._get_device_index(device_name, kind="output")

    def _get_device_index(
        self, device_name: str, kind: str = None
    ) -> Optional[int]:
        """Get the index of a device by name and kind."""
        devices = sd.query_devices()
        default_device = "pulse" if device_name == "" else device_name

        for device in devices:
            if kind and device.get("max_" + kind + "_channels", 0) <= 0:
                continue
            if device["name"] == default_device:
                return device["index"]
        return None

    def initialize_input_stream(
        self,
        samplerate: int = 16000,
        channels: int = 1,
        device_name: str = "pulse",
    ) -> bool:
        """Initialize the input (recording) stream."""
        try:
            device_index = self.get_input_device_index(device_name)
            if device_index is None:
                self.logger.error(f"Input device '{device_name}' not found")
                return False

            self._stop_input_stream()
            self._in_stream = sd.InputStream(
                samplerate=samplerate, channels=channels, device=device_index
            )
            self._in_stream.start()
            self.logger.info(
                f"Input stream initialized with device: {device_name}"
            )
            return True
        except sd.PortAudioError as e:
            self.logger.error(f"Failed to initialize input stream: {e}")
            self._in_stream = None
            return False

    def initialize_output_stream(
        self,
        samplerate: int = 24000,
        channels: int = 1,
        device_name: str = "pulse",
    ) -> bool:
        """Initialize the output (playback) stream."""
        try:
            device_index = self.get_output_device_index(device_name)
            if device_index is None:
                self.logger.error(f"Output device '{device_name}' not found")
                return False

            self._stop_output_stream()
            self._out_stream = sd.OutputStream(
                samplerate=samplerate, channels=channels, device=device_index
            )
            self._out_stream.start()
            self.logger.info(
                f"Output stream initialized with device: {device_name}"
            )
            return True
        except sd.PortAudioError as e:
            self.logger.error(f"Failed to initialize output stream: {e}")
            self._out_stream = None
            return False

    def write_to_output(self, data: Any) -> bool:
        """Write audio data to the output stream."""
        if self._out_stream and self._out_stream.active:
            try:
                self._out_stream.write(data)
                return True
            except sd.PortAudioError as e:
                self.logger.error(f"Error writing to output stream: {e}")
        return False

    def read_from_input(self, frames: int) -> tuple:
        """Read audio data from the input stream."""
        if self._in_stream and self._in_stream.active:
            try:
                return self._in_stream.read(frames)
            except sd.PortAudioError as e:
                self.logger.error(f"Error reading from input stream: {e}")
        return None, False

    def _stop_input_stream(self):
        """Stop and clean up the input stream."""
        if self._in_stream:
            try:
                self._in_stream.stop()
                self._in_stream.close()
            except Exception as e:
                self.logger.error(f"Error stopping input stream: {e}")
            self._in_stream = None

    def _stop_output_stream(self):
        """Stop and clean up the output stream."""
        if self._out_stream:
            try:
                self._out_stream.stop()
                self._out_stream.close()
            except Exception as e:
                self.logger.error(f"Error stopping output stream: {e}")
            self._out_stream = None

    def stop_all_streams(self):
        """Stop all audio streams."""
        self._stop_input_stream()
        self._stop_output_stream()
