import torch
import numpy as np
import sounddevice as sd

from transformers import AutoProcessor, WhisperForConditionalGeneration, AutoFeatureExtractor

from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QThread

from airunner.aihandler.logger import Logger
from airunner.workers.worker import Worker
from airunner.mediator_mixin import MediatorMixin


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
        settings = self.application_settings.value("settings")
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


class AudioProcessorWorker(Worker):
    """
    This class is responsible for processing audio.
    It will process audio from the audio_queue and send it to the model.
    """ 
    fs = 0

    def __init__(self, prefix):
        super().__init__(prefix=prefix)
        self.stt = SpeechToText()
        self.register("stt_audio_processed", self)
    
    def on_stt_audio_processed(self, transcription):
        self.emit("response_signal", transcription)

    def handle_message(self, audio_data):
        self.emit("processed_audio", audio_data)
    
    def update_properties(self):
        settings = self.application_settings.value("settings")
        self.fs = settings["stt_settings"]["fs"]


class STTController(QObject, MediatorMixin):
    logger = Logger(prefix="STTController")
    
    def __init__(self, *args, **kwargs):
        MediatorMixin.__init__(self)
        self.engine = kwargs.pop("engine", None)
        self.app = self.engine.app
        super().__init__(*args, **kwargs)

        # Audio capture worker and thread
        self.worker = self.create_worker(AudioCaptureWorker)
        
        # # Audio processor worker and thread
        self.audio_processor_worker = self.create_worker(AudioProcessorWorker)
        
        self.register("AudioCaptureWorker_response_signal", self)
        self.register("AudioProcessorWorker_processed_audio", self)

    def on_AudioCaptureWorker_response_signal(self, message: np.ndarray):
        self.logger.info("Heard signal")
        self.audio_processor_worker.add_to_queue(message)

    def on_AudioProcessorWorker_processed_audio(self, message: np.ndarray):
        self.logger.info("Processed audio")
        self.emit("processed_audio", message)
        

class SpeechToText(QObject, MediatorMixin):
    logger = Logger(prefix="SpeechToText")
    listening = False
    move_to_cpu_signal = pyqtSignal()

    def on_process_audio(self, audio_data, fs):
        inputs = np.squeeze(audio_data)
        inputs = self.feature_extractor(inputs, sampling_rate=fs, return_tensors="pt")
        inputs = inputs.to(self.model.device)
        transcription = self.run(inputs)
        self.emit("stt_audio_processed", transcription)

    def on_move_to_cpu(self):
        self.logger.info("Moving model to CPU")
        self.model = self.model.to("cpu")

    def __init__(self):
        super().__init__()
        MediatorMixin.__init__(self)
        self.load_model()
        self.register("move_to_cpu_signal", self)
        self.register("process_audio", self)

    @property
    def device(self):
        return torch.device("cuda" if self.use_cuda else "cpu")
    
    @property
    def use_cuda(self):
        return torch.cuda.is_available()

    def load_model(self):
        self.logger.info("Loading model")
        self.model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-tiny.en").to(self.device)
        self.processor = AutoProcessor.from_pretrained("openai/whisper-tiny.en")
        self.feature_extractor = AutoFeatureExtractor.from_pretrained("openai/whisper-base")

    is_on_gpu = False
    def move_to_gpu(self):
        if not self.is_on_gpu:
            self.logger.info("Moving model to GPU")
            self.model = self.model.to(self.device)
            self.processor = self.processor
            self.feature_extractor = self.feature_extractor
            self.is_on_gpu = True

    def move_inputs_to_device(self, inputs):
        if self.use_cuda:
            self.logger.info("Moving inputs to CUDA")
            try:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            except AttributeError:
                pass
        return inputs

    def run(self, inputs):
        self.logger.info("Running model")
        input_features = inputs.input_features
        input_features = self.move_inputs_to_device(input_features)
        generated_ids = self.model.generate(inputs=input_features)
        transcription = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        transcription = transcription.strip()
        print("transcription: ", transcription)
        if len(transcription) == 0 or len(transcription.split(" ")) == 1:
            return None
        return transcription
