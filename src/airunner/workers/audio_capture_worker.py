import sounddevice as sd
from PyQt6.QtCore import pyqtSlot, QThread

from airunner.workers.worker import Worker


class AudioCaptureWorker(Worker):
    """
    This class is responsible for capturing audio from the microphone.
    It will capture audio for a specified duration and then send the audio to the audio_processor_worker.
    """
    duration = 0
    fs = 0
    channels = 0

    def __init__(self, prefix):
        super().__init__(prefix)
        self.running = False
        self.listening = False
    
    def update_properties(self):
        settings = self.settings
        self.duration = settings["stt_settings"]["duration"]
        self.fs = settings["stt_settings"]["fs"]
        self.channels = settings["stt_settings"]["channels"]

    @pyqtSlot()
    def start(self):
        self.logger.info("Starting")
        self.running = True
        self.start_listening()
        while self.running:
            while self.listening:
                self.recording = sd.rec(int(self.duration * self.fs), samplerate=self.fs, channels=self.channels)
                sd.wait()
                self.handle_message(self.recording)
            while not self.listening:
                QThread.msleep(100)

    def start_listening(self):
        self.logger.info("Start listening")
        self.listening = True

    def stop_listening(self):
        self.logger.info("Stop listening")
        self.listening = False