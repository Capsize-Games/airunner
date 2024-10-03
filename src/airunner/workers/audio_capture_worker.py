import queue
import time

import sounddevice as sd
import numpy as np
from PySide6.QtCore import QThread, Slot

from airunner.aihandler.stt.whisper_handler import WhisperHandler
from airunner.enums import SignalCode, ModelStatus
from airunner.settings import SLEEP_TIME_IN_MS
from airunner.workers.worker import Worker


class AudioCaptureWorker(Worker):
    """
    This class is responsible for capturing audio from the microphone.
    It will capture audio when it detects voice activity and then send the audio to the audio_processor_worker.
    """

    def __init__(self, prefix):
        super().__init__(prefix=prefix)
        self.listening: bool = False
        self.voice_input_start_time: time.time = None
        self.chunk_duration = self.stt_settings.chunk_duration  # duration of chunks in milliseconds
        self.fs = self.stt_settings.fs
        self.stream = None
        self._audio_process_queue = queue.Queue()

    def on_start_capture_signal(self):
        self._start_listening()

    def on_stop_capture_signal(self):
        self._stop_listening()

    def start(self):
        self.logger.debug("Starting audio capture worker")
        running = True
        chunk_duration = self.stt_settings.chunk_duration
        fs = self.stt_settings.fs
        volume_input_threshold = self.stt_settings.volume_input_threshold
        silence_buffer_seconds = self.stt_settings.silence_buffer_seconds
        voice_input_start_time = None
        recording = []
        is_receiving_input = False
        while running:
            while self.listening and running and self.stream:
                try:
                    chunk, overflowed = self.stream.read(int(chunk_duration * fs))
                except sd.PortAudioError as e:
                    QThread.msleep(SLEEP_TIME_IN_MS)
                    continue
                if np.max(np.abs(chunk)) > volume_input_threshold:  # check if chunk is not silence
                    is_receiving_input = True
                    self.emit_signal(SignalCode.INTERRUPT_PROCESS_SIGNAL)
                    voice_input_start_time = time.time()
                elif voice_input_start_time is not None:
                    # make voice_end_time silence_buffer_seconds after voice_input_start_time
                    end_time = voice_input_start_time + silence_buffer_seconds
                    if time.time() >= end_time:
                        if len(recording) > 0:
                            self.emit_signal(
                                SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL,
                                {
                                    "item": b''.join(recording)
                                }
                            )
                            recording = []
                            is_receiving_input = False
                if is_receiving_input:
                    chunk_bytes = np.int16(chunk * 32767).tobytes()  # convert to bytes
                    recording.append(chunk_bytes)

            while not self.listening and running:
                QThread.msleep(SLEEP_TIME_IN_MS)

    def _start_listening(self):
        self.logger.debug("Start listening")
        self.listening = True
        fs = self.stt_settings.fs
        channels = self.stt_settings.channels
        if self.stream is None:
            self.stream = sd.InputStream(samplerate=fs, channels=channels)

        try:
            self.stream.start()
        except Exception as e:
            self.logger.error(e)

    def _stop_listening(self):
        self.logger.debug("Stop listening")
        self.listening = False
        try:
            self.stream.stop()
        except Exception as e:
            self.logger.error(e)

        try:
            self.stream.close()
        except Exception as e:
            self.logger.error(e)
