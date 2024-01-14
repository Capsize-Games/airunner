import torch
import numpy as np
import sounddevice as sd
import threading
import queue
import time

from PyQt6.QtCore import QObject

from transformers import AutoProcessor, WhisperForConditionalGeneration, AutoFeatureExtractor
from airunner.aihandler.logger import Logger


class SpeechToText(QObject):
    listening = False

    def __init__(self, engine=None, duration=5.0, fs=16000, hear_signal=None):
        super().__init__()
        self.engine = engine
        self.duration = duration
        self.fs = fs
        self.hear_signal = hear_signal
        self.model, self.processor, self.feature_extractor = self.load_whisper_model()
        self.audio_queue = queue.Queue()

    @property
    def device(self):
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def load_whisper_model(self):
        Logger.info("Loading whisper model...")
        model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-tiny.en").to(self.device)
        processor = AutoProcessor.from_pretrained("openai/whisper-tiny.en")
        feature_extractor = AutoFeatureExtractor.from_pretrained("openai/whisper-base")
        return model, processor, feature_extractor

    def move_to_cpu(self):
        self.model = self.model.to("cpu")

    def move_to_gpu(self):
        self.model = self.model.to(self.device)
        self.processor = self.processor
        self.feature_extractor = self.feature_extractor

    def run(self, inputs):
        print("Running whisper model...")
        input_features = inputs.input_features
        generated_ids = self.model.generate(inputs=input_features)
        transcription = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        # strip whitespace
        transcription = transcription.strip()
        print("transcription: ", transcription)
        # check if transcription is empty or contains a single word
        if len(transcription) == 0 or len(transcription.split(" ")) == 1:
            return None
        return transcription

    def capture_audio(self):
        Logger.info("Capturing audio...")
        while True:
            recording = sd.rec(int(self.duration * self.fs), samplerate=self.fs, channels=1)
            sd.wait()
            self.audio_queue.put(recording)

    def process_audio(self):
        while self.listening:
            Logger.info("self.listening...")
            if not self.audio_queue.empty():
                audio_data = self.audio_queue.get()
                # convert audio_data into a numpy array
                inputs = np.squeeze(audio_data)
                inputs = self.feature_extractor(inputs, sampling_rate=self.fs, return_tensors="pt")
                inputs = inputs.to(self.model.device)
                transcription = self.run(inputs)
                if transcription is not None:
                    # pause until we get a listen_signal
                    self.listening = False
                    self.hear_signal.emit(transcription)
        self.move_to_cpu()
        while not self.listening:
            time.sleep(0.1)
                    
    def do_listen(self):
        self.move_to_gpu()
        self.listening = True

    def listen(self):
        """
        This function will listen for audio and convert it to text.
        It triggers the hear_signal which is connected to the engine.hear function.
        """
        Logger.info("Listening...")
        capture_thread = threading.Thread(target=self.capture_audio)
        process_thread = threading.Thread(target=self.process_audio)

        capture_thread.start()
        process_thread.start()