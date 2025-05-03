import sounddevice as sd
from typing import Optional
from queue import Queue
import numpy as np
import librosa  # Import librosa for resampling

from PySide6.QtCore import QThread

from airunner.enums import SignalCode, TTSModel
from airunner.settings import AIRUNNER_SLEEP_TIME_IN_MS
from airunner.workers.worker import Worker


class TTSVocalizerWorker(Worker):
    """
    Speech (in the form of numpy arrays generated with the TTS class) is added to the
    vocalizer's queue. The vocalizer plays the speech using sounddevice.
    """

    reader_mode_active = False

    def __init__(self):
        self.signal_handlers = {
            SignalCode.INTERRUPT_PROCESS_SIGNAL: self.on_interrupt_process_signal,
            SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL: self.on_unblock_tts_generator_signal,
            SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL: self.on_tts_generator_worker_add_to_stream_signal,
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL: self.on_application_settings_changed_signal,
            SignalCode.PLAYBACK_DEVICE_CHANGED: self.on_playback_device_changed_signal,
        }
        super().__init__()
        self.queue = Queue()
        self.started = False
        self.do_interrupt = False
        self.accept_message = True
        self._model_samplerate: Optional[int] = (
            None  # Store the model's native sample rate
        )
        self._stream_samplerate: Optional[int] = (
            None  # Store the actual stream sample rate
        )
        self._device_default_samplerate: Optional[int] = (
            None  # Store device default
        )

    @property
    def is_espeak(self) -> bool:
        return self.chatbot_voice_model_type == TTSModel.ESPEAK.value

    def on_interrupt_process_signal(self):
        self.stop_stream()
        self.accept_message = False
        self.queue = Queue()

    def on_unblock_tts_generator_signal(self):
        if self.application_settings.tts_enabled:
            self.logger.debug("Starting TTS stream...")
            self.accept_message = True
            self.start_stream()

    def on_application_settings_changed_signal(self, data):
        if (
            data
            and data.get("setting_name", "") == "speech_t5_settings"
            and data.get("column_name", "") == "pitch"
        ):
            pitch = data.get("value", 0)
            self.stop_stream()
            self.start_stream(pitch)

    def on_playback_device_changed_signal(self):
        self.logger.debug(f"Playback device changed")
        self.stop_stream()
        self.start_stream()

    def stop_stream(self):
        if self.is_espeak:
            return
        self.logger.info("Stopping TTS vocalizer stream...")
        if self.api.sounddevice_manager.out_stream:
            self.api.sounddevice_manager._stop_output_stream()

    def start_stream(self, pitch: Optional[int] = None):
        if self.is_espeak:
            return
        self.logger.info("Starting TTS vocalizer stream...")

        # Determine the model's native sample rate
        if self.chatbot_voice_model_type == TTSModel.SPEECHT5:
            self._model_samplerate = 16000
        elif self.chatbot_voice_model_type == TTSModel.OPENVOICE:
            self._model_samplerate = 24000
        else:
            self._model_samplerate = 16000  # Default fallback
            self.logger.warning(
                f"Unknown TTS model type, defaulting model samplerate to {self._model_samplerate}"
            )

        try:
            device_info = sd.query_devices(self.playback_device, kind="output")
            self._device_default_samplerate = int(
                device_info.get("default_samplerate", 44100)
            )  # Use 44100 as fallback default
            self.logger.info(
                f"Playback device '{self.playback_device}' default sample rate: {self._device_default_samplerate}"
            )

            # First, try initializing with the model's native sample rate
            self.logger.info(
                f"Attempting to initialize stream with model sample rate: {self._model_samplerate}"
            )
            initialized = self._initialize_stream(self._model_samplerate)

            if not initialized:
                # If model rate failed, try the device's default sample rate
                self.logger.warning(
                    f"Failed to initialize with model sample rate {self._model_samplerate}. "
                    f"Falling back to device default sample rate: {self._device_default_samplerate}"
                )
                initialized = self._initialize_stream(
                    self._device_default_samplerate
                )

            if not initialized:
                self.logger.error(
                    "Failed to initialize audio stream with both model and default sample rates."
                )
                self.api.sounddevice_manager.out_stream = (
                    None  # Ensure stream is None
                )
                self._stream_samplerate = None

        except Exception as e:
            self.logger.error(
                f"Error querying device or starting audio stream: {e}"
            )
            # Use the manager's method to stop the stream
            self.api.sounddevice_manager._stop_output_stream()
            self._stream_samplerate = None

    @property
    def playback_device(self):
        playback_device = self.sound_settings.playback_device
        return playback_device if playback_device != "" else "pulse"

    def _initialize_stream(self, samplerate: int) -> bool:
        """Attempts to initialize the output stream with the given samplerate. Returns True on success, False on failure."""
        self.logger.info(
            f"Initializing TTS stream with samplerate: {samplerate}"
        )
        try:
            self.api.sounddevice_manager.initialize_output_stream(
                samplerate=samplerate,
                channels=1,
                device_name=self.playback_device,
            )
            if self.api.sounddevice_manager.out_stream:
                self._stream_samplerate = (
                    samplerate  # Store the successful sample rate
                )
                self.logger.info(
                    f"Successfully initialized stream with samplerate: {self._stream_samplerate}"
                )
                return True
            else:
                self.logger.error(
                    "Stream object is None after initialization attempt."
                )
                return False
        except sd.PortAudioError as e:
            if e.args[0] == sd.PaErrorCode.INVALID_SAMPLE_RATE:
                self.logger.warning(
                    f"Invalid sample rate {samplerate} for device '{self.playback_device}'."
                )
            else:
                self.logger.error(
                    f"PortAudioError initializing stream with samplerate {samplerate}: {e}"
                )
            # Use the manager's method to stop the stream
            self.api.sounddevice_manager._stop_output_stream()
            return False
        except Exception as e:
            self.logger.error(
                f"Unexpected error initializing stream with samplerate {samplerate}: {e}"
            )
            # Use the manager's method to stop the stream
            self.api.sounddevice_manager._stop_output_stream()
            return False

    def on_tts_generator_worker_add_to_stream_signal(self, response: dict):
        if self.accept_message:
            self.logger.debug("Adding speech to stream...")
            self.add_to_queue(response["message"])

    def handle_message(self, item):
        if not self.accept_message or item is None:
            return
        # Ensure stream is initialized
        if self.api.sounddevice_manager.out_stream is None:
            self.logger.warning(
                "Output stream is not initialized. Attempting to start."
            )
            self.start_stream()
            # If still no stream after attempting to start, exit
            if self.api.sounddevice_manager.out_stream is None:
                self.logger.error("Failed to start stream. Cannot play audio.")
                return

        # Resample if necessary
        resampled_item = item
        if (
            self._model_samplerate
            and self._stream_samplerate
            and self._model_samplerate != self._stream_samplerate
        ):
            self.logger.debug(
                f"Resampling audio from {self._model_samplerate} Hz to {self._stream_samplerate} Hz"
            )
            # Perform resampling with error handling
            try:
                # Ensure item is float32 for librosa
                item_float = item.astype(np.float32)
                resampled_item = librosa.resample(
                    item_float,
                    orig_sr=self._model_samplerate,
                    target_sr=self._stream_samplerate,
                )
                self.logger.debug("Resampling complete successfully")
            except Exception as e:
                self.logger.error(
                    f"Error during librosa resampling: {e}", exc_info=True
                )
                # Keep resampled_item as the original item if resampling fails
                self.logger.warning(
                    "Using original non-resampled audio due to resampling error"
                )
                resampled_item = item

        # Add debug statement to check we got past resampling
        self.logger.debug(
            "Resampling complete or bypassed. Proceeding to write check."
        )

        # Check if stream exists before write
        self.logger.debug(
            f"Checking stream before write: stream exists = {self.api.sounddevice_manager.out_stream is not None}"
        )

        # Write (potentially resampled) audio data
        if self.api.sounddevice_manager.out_stream:
            self.logger.debug(
                f"Attempting to write audio data with shape: {resampled_item.shape}, dtype: {resampled_item.dtype}"
            )
            success = self.api.sounddevice_manager.write_to_output(
                resampled_item
            )
            self.logger.debug(f"write_to_output returned: {success}")
            if success:
                self.started = True
            else:
                # If write fails, maybe the stream closed? Attempt restart next time.
                self.logger.warning(
                    "Failed to write to audio stream. Stream might be closed."
                )
                # Use the manager's method to stop the stream
                self.api.sounddevice_manager._stop_output_stream()
                self._stream_samplerate = None
        else:
            self.logger.warning(
                "Cannot write audio, output stream is None in worker."
            )

        QThread.msleep(AIRUNNER_SLEEP_TIME_IN_MS)

    def handle_speech(self, generated_speech):
        self.logger.debug("Adding speech to stream...")
        try:
            self.queue.put(generated_speech)
        except Exception as e:
            self.logger.error(f"Error while adding speech to stream: {e}")
