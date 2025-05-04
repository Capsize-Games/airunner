import sounddevice as sd
from typing import Optional, Dict, Any
import logging
import numpy as np


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
        # Add lock to prevent race conditions when multiple workers access the streams
        self._initialized = False

    @property
    def in_stream(self):
        if not self._in_stream:
            self.initialize_input_stream()
        return self._in_stream

    @property
    def out_stream(self):
        if not self._out_stream:
            self.initialize_output_stream()
        return self._out_stream

    @property
    def initialized(self):
        return self._initialized

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
        try:
            devices = sd.query_devices()
            default_device = "pulse" if device_name == "" else device_name

            # Try to find exact match first
            for device in devices:
                if kind and device.get("max_" + kind + "_channels", 0) <= 0:
                    continue
                if device["name"] == default_device:
                    return device["index"]

            # If no exact match, try substring match as fallback
            for device in devices:
                if kind and device.get("max_" + kind + "_channels", 0) <= 0:
                    continue
                if default_device.lower() in device["name"].lower():
                    self.logger.debug(f"Using partial match: {device['name']}")
                    return device["index"]

            # Last resort - use system default
            if kind == "input":
                default_idx = sd.default.device[0]
                self.logger.debug(
                    f"Using system default input device index: {default_idx}"
                )
                return default_idx
            elif kind == "output":
                default_idx = sd.default.device[1]
                self.logger.debug(
                    f"Using system default output device index: {default_idx}"
                )
                return default_idx

            return None
        except Exception as e:
            self.logger.error(f"Error getting device index: {e}")
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
                f"Input stream initialized with device: {device_name} (index: {device_index})"
            )
            self._initialized = True
            return True
        except sd.PortAudioError as e:
            self.logger.error(f"Failed to initialize input stream: {e}")
            self._in_stream = None
            return False
        except Exception as e:
            self.logger.error(
                f"Unexpected error initializing input stream: {e}"
            )
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
                f"Output stream initialized with device: {device_name} (index: {device_index})"
            )
            self._initialized = True
            return True
        except sd.PortAudioError as e:
            self.logger.error(f"Failed to initialize output stream: {e}")
            self._out_stream = None
            return False
        except Exception as e:
            self.logger.error(
                f"Unexpected error initializing output stream: {e}"
            )
            self._out_stream = None
            return False

    def write_to_output(self, data: Any) -> bool:
        """Write audio data to the output stream."""
        if self._out_stream and self._out_stream.active:
            try:
                # Make sure we're dealing with a numpy array
                if not isinstance(data, np.ndarray):
                    data = np.array(data)

                # Log the audio statistics to help with debugging
                self.logger.debug(
                    f"Audio data stats before write: shape={data.shape}, dtype={data.dtype}, "
                    + f"min={np.min(data) if data.size > 0 else 'empty'}, "
                    + f"max={np.max(data) if data.size > 0 else 'empty'}, "
                    + f"mean={np.mean(data) if data.size > 0 else 'empty'}"
                )

                # If audio is too quiet (common with some models), amplify it
                # Check if audio is very quiet
                if data.size > 0 and np.abs(data).max() < 0.1:
                    # Increase volume to a reasonable level
                    amp_factor = (
                        0.5 / np.abs(data).max()
                        if np.abs(data).max() > 0
                        else 1.0
                    )
                    data = data * amp_factor
                    self.logger.debug(
                        f"Amplified audio by factor {amp_factor}"
                    )

                # Ensure audio is in the correct format for the output stream
                # PortAudio typically expects float32 data in the range [-1.0, 1.0]
                if data.dtype != np.float32:
                    data = data.astype(np.float32)

                # Ensure we have the correct number of channels
                if len(data.shape) == 1 and self._out_stream.channels > 1:
                    # Convert mono to stereo/multichannel if needed
                    data = np.tile(
                        data.reshape(-1, 1), (1, self._out_stream.channels)
                    )
                    self.logger.debug(
                        f"Converted mono to {self._out_stream.channels} channels"
                    )

                self._out_stream.write(data)
                self.logger.debug("Successfully wrote data to output stream.")
                return True
            except sd.PortAudioError as e:
                self.logger.error(
                    f"PortAudioError writing to output stream: {e}"
                )
            except Exception as e:  # Catch other potential errors during write
                self.logger.error(
                    f"Unexpected error writing to output stream: {e}"
                )
        else:
            self.logger.warning(
                "Attempted to write to inactive/closed output stream."
            )
        return False

    def read_from_input(self, frames: int) -> tuple:
        """Read audio data from the input stream."""
        if self._in_stream and self._in_stream.active:
            try:
                return self._in_stream.read(frames)
            except sd.PortAudioError as e:
                self.logger.error(f"Error reading from input stream: {e}")
            except Exception as e:
                self.logger.error(
                    f"Unexpected error reading from input stream: {e}"
                )
        return None, False

    def _stop_input_stream(self):
        """Stop and clean up the input stream."""
        if self._in_stream:
            try:
                self._in_stream.stop()
                self._in_stream.close()
                self.logger.debug(
                    "Input stream stopped and closed successfully"
                )
            except Exception as e:
                self.logger.error(f"Error stopping input stream: {e}")
            self._in_stream = None

    def _stop_output_stream(self):
        """Stop and clean up the output stream."""
        if self._out_stream:
            try:
                self._out_stream.stop()
                self._out_stream.close()
                self.logger.debug(
                    "Output stream stopped and closed successfully"
                )
            except Exception as e:
                self.logger.error(f"Error stopping output stream: {e}")
            self._out_stream = None

    def stop_all_streams(self):
        """Stop all audio streams."""
        self._stop_input_stream()
        self._stop_output_stream()
        self._initialized = False
