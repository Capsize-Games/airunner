import sounddevice as sd
from PyQt6.QtCore import pyqtSlot, QThread

from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class AudioCaptureWorker(Worker):
    """
    This class is responsible for capturing audio from the microphone.
    It will capture audio for a specified duration and then send the audio to the audio_processor_worker.
    """

    def __init__(self, prefix):
        super().__init__(prefix)
        self.recording = None
        self.running = False
        self.listening = False
        self.duration = 10
        self.fs = 16000
        self.channels = 1
        self.update_properties()
    
    def update_properties(self):
        settings = self.settings
        self.duration = settings["stt_settings"]["duration"]
        self.fs = settings["stt_settings"]["fs"]
        self.channels = settings["stt_settings"]["channels"]

    def start(self):
        self.logger.info("Starting")
        self.running = True
        self.start_listening()
        while self.running:
            while self.listening and self.running:
                try:
                    self.recording = sd.rec(
                        int(self.duration * self.fs),
                        samplerate=self.fs,
                        channels=self.channels
                    )
                except Exception as e:
                    self.logger.error(e)
                    self.stop_listening()
                    continue
                sd.wait()
                self.handle_message(self.recording)
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