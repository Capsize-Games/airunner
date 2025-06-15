import queue
import time

import numpy as np
from PySide6.QtCore import QThread

from airunner.enums import SignalCode, ModelStatus
from airunner.settings import AIRUNNER_SLEEP_TIME_IN_MS
from airunner.workers.worker import Worker


class AudioCaptureWorker(Worker):
    """
    This class is responsible for capturing audio from the microphone.
    It will capture audio when it detects voice activity and then send the audio to the audio_processor_worker.
    """

    def __init__(self):
        self.signal_handlers = {
            SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL: self.on_audio_capture_worker_response_signal,
            SignalCode.STT_START_CAPTURE_SIGNAL: self.on_stt_start_capture_signal,
            SignalCode.STT_STOP_CAPTURE_SIGNAL: self.on_stt_stop_capture_signal,
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL: self.on_model_status_changed_signal,
            SignalCode.RECORDING_DEVICE_CHANGED: self.on_recording_device_changed_signal,
        }
        super().__init__()
        self.listening: bool = False
        self.voice_input_start_time: time.time = None
        self.chunk_duration = (
            self.stt_settings.chunk_duration
        )  # duration of chunks in milliseconds
        self.fs = self.stt_settings.fs
        self.running = False
        self._use_playback_stream: bool = False
        self._audio_process_queue = queue.Queue()

    @property
    def recording_device(self):
        """
        Get the recording device name from the sound settings.
        """
        recording_device = self.sound_settings.recording_device
        return recording_device if recording_device != "" else "pulse"

    def on_audio_capture_worker_response_signal(self, message: dict):
        item: np.ndarray = message["item"]
        self.logger.debug("Heard signal")
        self.add_to_queue(item)

    def on_stt_start_capture_signal(self):
        if not self.listening:
            self._start_listening()

    def on_stt_stop_capture_signal(self):
        if self.listening:
            self._stop_listening()

    def on_model_status_changed_signal(self, message: dict):
        model = message["model"]
        status = message["status"]
        if model == "stt" and status is ModelStatus.LOADED:
            self._start_listening()
        elif model == "stt" and status in (
            ModelStatus.UNLOADED,
            ModelStatus.FAILED,
        ):
            self._stop_listening()

    def run_thread(self):
        self.logger.debug("Starting audio capture worker")
        self.running = True
        chunk_duration = self.stt_settings.chunk_duration
        volume_input_threshold = self.stt_settings.volume_input_threshold
        silence_buffer_seconds = self.stt_settings.silence_buffer_seconds
        voice_input_start_time = None
        recording = []
        is_receiving_input = False

        while (
            self.listening
            and self.running
            and self.api.sounddevice_manager.in_stream
        ):
            try:
                # Use the actual sample rate from the stream if available
                actual_fs = (
                    self.api.sounddevice_manager.in_stream.samplerate
                    if hasattr(
                        self.api.sounddevice_manager.in_stream,
                        "samplerate",
                    )
                    else self.stt_settings.fs
                )
                frames = int(chunk_duration * actual_fs)
                chunk_data = self.api.sounddevice_manager.read_from_input(
                    frames
                )

                if chunk_data is None or chunk_data[0] is None:
                    QThread.msleep(AIRUNNER_SLEEP_TIME_IN_MS)
                    continue

                chunk, overflowed = chunk_data
                if chunk.ndim > 1:
                    chunk = np.mean(chunk, axis=1)
            except Exception as e:
                self.logger.error(f"Error reading from input stream: {e}")
                QThread.msleep(AIRUNNER_SLEEP_TIME_IN_MS)
                continue

            if (
                self._use_playback_stream
                and self.api.sounddevice_manager.out_stream
            ):
                try:
                    self.api.sounddevice_manager.write_to_output(chunk)
                except Exception as e:
                    self.logger.error(f"Playback error: {e}")

            if (
                np.max(np.abs(chunk)) > volume_input_threshold
            ):  # check if chunk is not silence
                self.logger.debug("Heard voice")

                is_receiving_input = True
                self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)
                voice_input_start_time = time.time()
            elif voice_input_start_time is not None:
                # make voice_end_time silence_buffer_seconds after voice_input_start_time
                end_time = voice_input_start_time + silence_buffer_seconds
                if time.time() >= end_time:
                    if len(recording) > 0:
                        self.logger.debug(
                            "Sending audio to audio_processor_worker"
                        )
                        self.emit_signal(
                            SignalCode.UNBLOCK_TTS_GENERATOR_SIGNAL,
                            {
                                "callback": lambda _recording=recording: self.emit_signal(
                                    SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL,
                                    {"item": b"".join(_recording)},
                                )
                            },
                        )
                        recording = []
                        is_receiving_input = False
            if is_receiving_input:
                chunk_bytes = np.int16(
                    chunk * 32767
                ).tobytes()  # convert to bytes
                recording.append(chunk_bytes)

        while not self.listening and self.running:
            QThread.msleep(AIRUNNER_SLEEP_TIME_IN_MS)

    def _start_listening(self):
        self.logger.debug("Start listening")
        self._initialize_stream()
        self.listening = True

    def _stop_listening(self):
        self.logger.debug("Stop listening")
        self.listening = False
        # Do not set self.running = False here - it terminates the worker
        # Allow proper cleanup to happen in the main loop

    def on_recording_device_changed_signal(self):
        self.logger.debug(f"Recording device changed")
        self._initialize_stream()

    def _initialize_stream(self):
        self.logger.debug("Initializing audio capture stream")
        samplerate = 16000  # self.stt_settings.fs
        channels = self.stt_settings.channels

        # Close any existing streams first to avoid conflicts
        if self.api.sounddevice_manager.in_stream:
            self.logger.debug(
                "Closing existing input stream before initializing a new one"
            )
            self.api.sounddevice_manager._stop_input_stream()

        # Log available input devices to help with debugging
        try:
            import sounddevice as sd

            devices = sd.query_devices()
            input_devices = [
                d for d in devices if d.get("max_input_channels", 0) > 0
            ]
            self.logger.debug(
                f"Available input devices: {[d['name'] for d in input_devices]}"
            )
            self.logger.debug(
                f"Selected recording device: {self.recording_device}"
            )
        except Exception as e:
            self.logger.error(f"Error querying audio devices: {e}")

        # Initialize input stream with better error handling
        success = self.api.sounddevice_manager.initialize_input_stream(
            samplerate=samplerate,
            channels=channels,
            device_name=self.recording_device,
        )

        if success:
            self.logger.info(
                f"Successfully initialized input stream with device: {self.recording_device}"
            )
        else:
            self.logger.error(
                f"Failed to initialize input stream with device: {self.recording_device}"
            )
            # Try with default device as fallback
            self.logger.warning("Attempting to initialize with default device")
            success = self.api.sounddevice_manager.initialize_input_stream(
                samplerate=samplerate,
                channels=channels,
                device_name="",  # Empty string should use system default
            )
            if success:
                self.logger.info(
                    "Successfully initialized input stream with default device"
                )
            else:
                self.logger.error(
                    "Failed to initialize input stream with default device"
                )

        # Initialize playback stream if needed
        if self._use_playback_stream:
            device_name = self.sound_settings.playback_device or "pulse"
            self.logger.debug(
                f"Initializing monitoring playback stream with device: {device_name}"
            )
            playback_success = (
                self.api.sounddevice_manager.initialize_output_stream(
                    samplerate=samplerate,
                    channels=channels,
                    device_name=device_name,
                )
            )
            if not playback_success:
                self.logger.error(
                    f"Failed to initialize playback stream with device: {device_name}"
                )

        # Verify stream status
        if self.api.sounddevice_manager.in_stream:
            self.logger.debug("Input stream is now active and ready")
        else:
            self.logger.error("Input stream failed to initialize properly")

        return self.api.sounddevice_manager.in_stream is not None
