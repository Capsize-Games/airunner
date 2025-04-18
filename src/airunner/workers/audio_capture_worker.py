import queue
import time

import sounddevice as sd
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
        self._selected_device = None
        super().__init__()
        self.listening: bool = False
        self.voice_input_start_time: time.time = None
        self.chunk_duration = (
            self.stt_settings.chunk_duration
        )  # duration of chunks in milliseconds
        self.fs = self.stt_settings.fs
        self.stream = None
        self._use_playback_stream: bool = False
        self.playback_stream = None
        self.running = False
        self._audio_process_queue = queue.Queue()

    @property
    def recording_device(self):
        """
        Get the recording device name from the sound settings.
        """
        recording_deivce = self.sound_settings.recording_device
        return recording_deivce if recording_deivce != "" else "pulse"

    @property
    def selected_device(self):
        if self._selected_device is None:
            devices = sd.query_devices()
            for device in devices:
                if device["name"] == self.recording_device:
                    self._selected_device = device
                    break
        return self._selected_device

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

    def start(self):
        self.logger.debug("Starting audio capture worker")
        self.running = True
        chunk_duration = self.stt_settings.chunk_duration
        volume_input_threshold = self.stt_settings.volume_input_threshold
        silence_buffer_seconds = self.stt_settings.silence_buffer_seconds
        voice_input_start_time = None
        recording = []
        is_receiving_input = False

        while self.running:
            while self.listening and self.running and self.stream:
                try:
                    # Use the actual sample rate from the stream if available
                    actual_fs = (
                        self.stream.samplerate
                        if hasattr(self.stream, "samplerate")
                        else self.stt_settings.fs
                    )
                    chunk, overflowed = self.stream.read(
                        int(chunk_duration * actual_fs)
                    )
                    if chunk.ndim > 1:
                        chunk = np.mean(chunk, axis=1)
                except sd.PortAudioError as e:
                    self.logger.error(f"PortAudioError: {e}")
                    QThread.msleep(AIRUNNER_SLEEP_TIME_IN_MS)
                    continue
                except Exception as e:
                    self.logger.error(e)
                    QThread.msleep(AIRUNNER_SLEEP_TIME_IN_MS)
                    continue

                if self.playback_stream:
                    try:
                        self.playback_stream.write(chunk)
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
                                SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL,
                                {"item": b"".join(recording)},
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

        # Stop playback stream
        if self.playback_stream:
            try:
                self.playback_stream.stop()
                self.playback_stream.close()
            except Exception as e:
                self.logger.error(f"Error stopping playback stream: {e}")

    def _start_listening(self):
        self.logger.debug("Start listening")
        if self.stream is not None:
            self._end_stream()
        self._initialize_stream()
        self.listening = True

    def _stop_listening(self):
        self.logger.debug("Stop listening")
        self.listening = False
        self.running = False
        self._end_stream()
        # self._capture_thread.join()

    def _end_stream(self):
        if self.stream:
            self.logger.info("Stopping audio capture stream")
            try:
                self.stream.stop()
            except Exception as e:
                self.logger.error(e)
            try:
                self.stream.close()
            except Exception as e:
                self.logger.error(e)
            try:
                self.stream.abort()
            except Exception as e:
                self.logger.error(e)
            self.stream = None

    def on_recording_device_changed_signal(self):
        self.logger.debug(f"Recording device changed")
        self._end_stream()
        self._initialize_stream()

    def _initialize_stream(self):
        self.logger.debug("Initializing audio capture stream")
        samplerate = 16000  # self.stt_settings.fs
        channels = self.stt_settings.channels

        if self.selected_device:
            try:
                self.stream = sd.InputStream(
                    samplerate=samplerate,
                    channels=channels,
                    device=self.selected_device["index"],
                )
                device_name = self.selected_device["name"]
                self.logger.info(
                    f"Audio stream initialized with sample rate: {samplerate}, channels: {channels}, device: {device_name}"
                )
                self.stream.start()
            except Exception as e:
                self.logger.error(f"Failed to initialize audio stream: {e}")
                self.stream = None
        else:
            self.logger.error(
                f"Recording device '{self.recording_device}' not found."
            )
            self.stream = None

        # Initialize playback stream
        self.playback_stream = None
        if self._use_playback_stream:
            try:
                self.playback_stream = sd.OutputStream(
                    samplerate=self.stream.samplerate,
                    channels=self.stt_settings.channels,
                )
                self.playback_stream.start()
            except Exception as e:
                self.logger.error(f"Failed to initialize playback stream: {e}")
                self.playback_stream = None
