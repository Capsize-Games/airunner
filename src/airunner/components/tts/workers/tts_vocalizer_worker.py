import sounddevice as sd
import inspect
from typing import Optional
from queue import Queue
import numpy as np
import librosa  # Import librosa for resampling

from PySide6.QtCore import QThread

from airunner.enums import TTSModel
from airunner.settings import AIRUNNER_SLEEP_TIME_IN_MS
from airunner.components.application.workers.worker import Worker
from airunner.utils.audio.sound_device_manager import SoundDeviceManager


class TTSVocalizerWorker(Worker):
    """
    Speech (in the form of numpy arrays generated with the TTS class) is added to the
    vocalizer's queue. The vocalizer plays the speech using sounddevice.
    """

    reader_mode_active = False

    def __init__(
        self,
        sleep_time_in_ms: int = AIRUNNER_SLEEP_TIME_IN_MS,
    ):
        super().__init__(sleep_time_in_ms=sleep_time_in_ms)
        self.queue = Queue()
        self.started = False
        self.do_interrupt = False
        self.accept_message = True
        self._local_sounddevice_manager: Optional[SoundDeviceManager] = None
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
        return self.chatbot_voice_model_type == TTSModel.ESPEAK

    def on_interrupt_process_signal(self, data: dict = None):
        self.stop_stream()
        self.accept_message = False
        self.queue = Queue()

    def on_unblock_tts_generator_signal(self, data: dict = None):
        if self.application_settings.tts_enabled:
            self.logger.debug("Starting TTS stream...")
            self.accept_message = True
            self.start_stream()

    def on_application_settings_changed_signal(self, data):
        pass

    def on_playback_device_changed_signal(self):
        self.logger.debug(f"Playback device changed")
        self.stop_stream()
        self.start_stream()

    def _current_api(self):
        """Return the freshest API reference available to this worker."""
        explicit_candidates = []
        refresher = getattr(self, "refresh_api_reference", None)
        if callable(refresher):
            explicit_candidates.append(refresher())
        explicit_candidates.append(getattr(self, "api", None))

        api = TTSVocalizerWorker._resolve_current_api_candidates(
            self,
            explicit_candidates,
        )
        if api is not None:
            return api

        candidates = []

        resolve_api = getattr(
            self,
            "_resolve_api_instance",
            TTSVocalizerWorker._resolve_api_instance,
        )
        candidates.append(resolve_api())

        main_window_getter = getattr(
            self,
            "_main_window",
            TTSVocalizerWorker._main_window,
        )
        candidates.append(main_window_getter())

        main_window_api_getter = getattr(
            self,
            "_main_window_api",
            TTSVocalizerWorker._main_window_api,
        )
        candidates.append(main_window_api_getter())

        fallback_api = None
        for candidate in candidates:
            candidate = TTSVocalizerWorker._normalize_api_candidate(candidate)
            if candidate is None or getattr(candidate, "headless", False):
                continue
            if TTSVocalizerWorker._candidate_has_sounddevice_manager(
                candidate
            ):
                self.api = candidate
                return candidate
            if fallback_api is None:
                fallback_api = candidate

        if fallback_api is not None:
            self.api = fallback_api
        return fallback_api

    @staticmethod
    def _resolve_current_api_candidates(worker, candidates):
        """Return one usable API from the provided candidate list."""
        fallback_api = None
        had_candidate = False
        for candidate in candidates:
            candidate = TTSVocalizerWorker._normalize_api_candidate(candidate)
            if candidate is None or getattr(candidate, "headless", False):
                continue
            had_candidate = True
            if TTSVocalizerWorker._candidate_has_sounddevice_manager(
                candidate
            ):
                worker.api = candidate
                return candidate
            if fallback_api is None:
                fallback_api = candidate

        if fallback_api is not None:
            worker.api = fallback_api
        if had_candidate:
            return fallback_api
        return None

    @staticmethod
    def _normalize_api_candidate(candidate):
        """Return one app-like API object from a nested candidate."""
        if candidate is None:
            return None

        root_api = getattr(candidate, "api", None)
        if root_api is not None and getattr(candidate, "daemon_client", None) is None:
            return root_api

        app_api = getattr(getattr(candidate, "app", None), "api", None)
        if app_api is not None and getattr(candidate, "daemon_client", None) is None:
            return app_api
        return candidate

    @staticmethod
    def _candidate_has_sounddevice_manager(candidate) -> bool:
        """Return whether one API-like object exposes sounddevice_manager."""
        try:
            return (
                inspect.getattr_static(
                    candidate,
                    "sounddevice_manager",
                    None,
                )
                is not None
            )
        except Exception:
            return getattr(candidate, "sounddevice_manager", None) is not None

    @staticmethod
    def _resolve_api_instance():
        """Resolve the live App/API object when worker init ran too early."""
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                return getattr(app, "api", None)
        except Exception:
            pass

        try:
            from airunner.components.server.api.server import get_api

            return get_api(create_if_missing=False)
        except Exception:
            return None

    @staticmethod
    def _main_window_api():
        """Return the API exposed by the active GUI main window."""
        main_window = TTSVocalizerWorker._main_window()
        if main_window is None:
            return None
        return getattr(main_window, "api", None) or getattr(
            getattr(main_window, "app", None),
            "api",
            None,
        )

    @staticmethod
    def _main_window():
        """Return the active GUI main window when one exists."""
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is None:
                return None
            return getattr(app, "main_window", None)
        except Exception:
            return None

    def _fallback_sounddevice_manager(self):
        """Return one local audio manager when no shared manager is usable."""
        manager = getattr(self, "_local_sounddevice_manager", None)
        if manager is None:
            self.logger.warning(
                "Falling back to a worker-local SoundDeviceManager for TTS playback"
            )
            manager = SoundDeviceManager()
            self._local_sounddevice_manager = manager
        return manager

    def _sounddevice_manager(self):
        """Return the sounddevice manager used for TTS playback."""
        api = TTSVocalizerWorker._current_api(self)
        if api is not None:
            try:
                manager = getattr(api, "sounddevice_manager", None)
                if manager is not None:
                    return manager
            except Exception:
                pass
        return TTSVocalizerWorker._fallback_sounddevice_manager(self)

    def stop_stream(self):
        if self.is_espeak:
            return
        self.logger.info("Stopping TTS vocalizer stream...")
        manager = TTSVocalizerWorker._sounddevice_manager(self)
        if manager is not None and manager.out_stream:
            manager._stop_output_stream()

    def start_stream(self, pitch: Optional[int] = None):
        if self.is_espeak:
            return
        self.logger.info("Starting TTS vocalizer stream...")
        manager = TTSVocalizerWorker._sounddevice_manager(self)

        if manager is None:
            self.logger.error(
                "TTS vocalizer API is missing sounddevice_manager"
            )
            self._stream_samplerate = None
            return

        # Determine the model's native sample rate
        if self.chatbot_voice_model_type == TTSModel.OPENVOICE:
            self._model_samplerate = 24000
        elif self.chatbot_voice_model_type == TTSModel.ESPEAK:
            self._model_samplerate = 16000
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
                manager.out_stream = None
                self._stream_samplerate = None

        except Exception as e:
            self.logger.error(
                f"Error querying device or starting audio stream: {e}"
            )
            # Use the manager's method to stop the stream
            manager._stop_output_stream()
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
        manager = TTSVocalizerWorker._sounddevice_manager(self)
        if manager is None:
            self.logger.error(
                "TTS vocalizer API is missing sounddevice_manager"
            )
            return False
        try:
            manager.initialize_output_stream(
                samplerate=samplerate,
                channels=1,
                device_name=self.playback_device,
            )
            if manager.out_stream:
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
            manager._stop_output_stream()
            return False
        except Exception as e:
            self.logger.error(
                f"Unexpected error initializing stream with samplerate {samplerate}: {e}"
            )
            # Use the manager's method to stop the stream
            manager._stop_output_stream()
            return False

    def on_tts_generator_worker_add_to_stream_signal(self, response: dict):
        if self.accept_message:
            self.logger.debug("Adding speech to stream...")
            self.add_to_queue(response["message"])

    def handle_message(self, item):
        if isinstance(item, dict) and item.get("_message_type") == "interrupt":
            self.on_interrupt_process_signal(item.get("data"))
            return
        if not self.accept_message or item is None:
            return
        manager = TTSVocalizerWorker._sounddevice_manager(self)
        if manager is None:
            self.logger.error(
                "TTS vocalizer API is missing sounddevice_manager"
            )
            return
        # Ensure stream is initialized
        if manager.out_stream is None:
            self.logger.warning(
                "Output stream is not initialized. Attempting to start."
            )
            self.start_stream()
            manager = TTSVocalizerWorker._sounddevice_manager(self)
            # If still no stream after attempting to start, exit
            if manager is None or manager.out_stream is None:
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
            f"Checking stream before write: stream exists = {manager.out_stream is not None}"
        )

        # Write (potentially resampled) audio data
        if manager.out_stream:
            self.logger.debug(
                f"Attempting to write audio data with shape: {resampled_item.shape}, dtype: {resampled_item.dtype}"
            )
            success = manager.write_to_output(resampled_item)
            self.logger.debug(f"write_to_output returned: {success}")
            if success:
                self.started = True
            else:
                # If write fails, maybe the stream closed? Attempt restart next time.
                self.logger.warning(
                    "Failed to write to audio stream. Stream might be closed."
                )
                # Use the manager's method to stop the stream
                manager._stop_output_stream()
                self._stream_samplerate = None
        else:
            self.logger.warning(
                "Cannot write audio, output stream is None in worker."
            )

        QThread.msleep(
            getattr(self, "_sleep_time_in_ms", AIRUNNER_SLEEP_TIME_IN_MS)
        )

    def handle_speech(self, generated_speech):
        self.logger.debug("Adding speech to stream...")
        try:
            self.queue.put(generated_speech)
        except Exception as e:
            self.logger.error(f"Error while adding speech to stream: {e}")
