import time

import sounddevice as sd
import numpy as np
from PyQt6.QtCore import QThread
from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class AudioCaptureWorker(Worker):
    """
    This class is responsible for capturing audio from the microphone.
    It will capture audio when it detects voice activity and then send the audio to the audio_processor_worker.
    """

    def __init__(self, prefix):
        super().__init__(prefix)
        self.recording = []
        self.running: bool = False
        self.listening: bool = False
        self.is_recieving_input: bool = False
        self.voice_input_start_time: time.time = None
        stt_settings = self.settings["stt_settings"]
        self.chunk_duration = stt_settings["chunk_duration"]  # duration of chunks in milliseconds
        self.fs = stt_settings["fs"]
        self.channels = stt_settings["channels"]
        self.volume_input_threshold = stt_settings["volume_input_threshold"]  # threshold for volume input
        self.silence_buffer_seconds = stt_settings["silence_buffer_seconds"]  # in seconds
        self.update_properties()
        self.register(
            SignalCode.STT_STOP_CAPTURE_SIGNAL,
            self.stop_listening
        )
        self.register(
            SignalCode.STT_START_CAPTURE_SIGNAL,
            self.start_listening
        )

    def update_properties(self):
        stt_settings = self.settings["stt_settings"]
        self.chunk_duration = stt_settings["chunk_duration"]
        self.fs = stt_settings["fs"]
        self.channels = stt_settings["channels"]
        self.volume_input_threshold = stt_settings["volume_input_threshold"]
        self.silence_buffer_seconds = stt_settings["silence_buffer_seconds"]

    def start(self):
        self.logger.info("Starting")
        self.running = True
        if self.settings["stt_enabled"]:
            self.start_listening()
        while self.running:
            while self.listening and self.running:
                chunk = sd.rec(
                    int(self.chunk_duration * self.fs),
                    samplerate=self.fs,
                    channels=self.channels,
                    dtype="float32"
                )
                sd.wait()
                if np.max(np.abs(chunk)) > self.volume_input_threshold:  # check if chunk is not silence
                    self.is_recieving_input = True
                    self.voice_input_start_time = time.time()
                else:
                    # make voice_end_time self.silence_buffer_seconds after voice_input_start_time
                    if self.voice_input_start_time is not None and time.time() >= self.voice_input_start_time + self.silence_buffer_seconds:
                        if len(self.recording) > 0:
                            self.handle_message(b''.join(self.recording))
                            self.recording = []
                            self.is_recieving_input = False
                if self.is_recieving_input:
                    chunk_bytes = np.int16(chunk * 32767).tobytes()  # convert to bytes
                    self.recording.append(chunk_bytes)

            while not self.listening and self.running:
                QThread.msleep(100)

    def handle_message(self, message):
        self.emit(
            SignalCode.AUDIO_CAPTURE_WORKER_RESPONSE_SIGNAL,
            message
        )

    def start_listening(self):
        self.logger.info("Start listening")
        self.listening = True

    def stop_listening(self):
        self.logger.info("Stop listening")
        self.listening = False