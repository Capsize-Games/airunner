import torch
import numpy as np
import sounddevice as sd
import threading
import queue
import time

from transformers import AutoProcessor, WhisperForConditionalGeneration, AutoFeatureExtractor

from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QThread

from airunner.aihandler.logger import Logger


class AudioCaptureWorker(QObject):
    """
    This class is responsible for capturing audio from the microphone.
    It will capture audio for a specified duration and then send the audio to the audio_processor_worker.
    """
    logger = Logger(prefix="AudioCaptureWorker")
    finished = pyqtSignal()

    def __init__(self, duration=5.0, fs=16000, audio_queue=None):
        super().__init__()
        self.duration = duration
        self.fs = fs
        self.audio_queue = audio_queue
        self.running = False
        self.listening = False
        self.thread = None
        self.is_recording = False
        self.recording = None

    def start_recording(self):
        self.is_recording = True
        self.thread = threading.Thread(target=self._record)
        self.thread.start()
    
    def stop_recording(self):
        self.is_recording = False
        if self.thread is not None:
            self.thread.join()
            self.thread = None
        self.recording = None
    
    def _record(self):
        self.recording = np.empty((self.fs * self.duration,))
        while self.is_recording:
            self.recording = np.append(self.recording, sd.rec(int(self.duration * self.fs), samplerate=self.fs, channels=1))
            sd.wait()
            self.audio_queue.put(self.recording)

    def run(self):
        self.logger.info("AudioCaptureWorker Starting")
        self.running = True
        self.start_listening()
        while self.running:
            while self.listening:
                time.sleep(0.1)
            while not self.listening:
                time.sleep(0.1)
    
    def stop(self):
        self.logger.info("AudioCaptureWorker Stopping")
        self.stop_listening()
        self.running = False

    def start_listening(self):
        self.logger.info("Start listening")
        self.listening = True
        self.start_recording()

    def stop_listening(self):
        self.logger.info("Stop listening")
        self.listening = False
        self.stop_recording()
        self.finished.emit()


class AudioProcessorWorker(QObject):
    """
    This class is responsible for processing audio.
    It will process audio from the audio_queue and send it to the model.
    """
    logger = Logger(prefix="AudioProcessorWorker")
    finished = pyqtSignal()

    def __init__(self, parent, fs=None, model=None, processor=None, feature_extractor=None, audio_queue=None):
        super().__init__()
        self.parent = parent
        self.fs = fs
        self.model = model
        self.processor = processor
        self.feature_extractor = feature_extractor
        self.audio_queue = audio_queue
        self.listening = False

    def run(self):
        self.logger.info("AudioProcessorWorker Starting")
        self.start_listening()
        while self.running:
            if not self.audio_queue.empty():
                audio_data = self.audio_queue.get()
                # convert audio_data into a numpy array
                inputs = np.squeeze(audio_data)
                inputs = self.feature_extractor(inputs, sampling_rate=self.fs, return_tensors="pt")
                inputs = inputs.to(self.model.device)
                transcription = self.parent.run(inputs)
                if transcription is not None:
                    self.stop_listening()
                    self.parent.hear_signal.emit(transcription)
            time.sleep(0.1)
    
    def stop(self):
        self.logger.info("Stopping")
        self.running = False
        self.finished.emit()
            

class SpeechToText(QObject):
    logger = Logger(prefix="SpeechToText")
    listening = False
    move_to_cpu_signal = pyqtSignal()

    @pyqtSlot()
    def move_to_cpu(self):
        self.logger.info("Moving model to CPU")
        self.model = self.model.to("cpu")

    def __init__(self, engine=None, duration=5.0, fs=16000, hear_signal=None):
        super().__init__()
        self.engine = engine
        self.duration = duration
        self.fs = fs
        self.hear_signal = hear_signal
        self.model, self.processor, self.feature_extractor = self.load_whisper_model()
        self.audio_queue = queue.Queue()

        self.move_to_cpu_signal.connect(self.move_to_cpu)

        # Audio capture worker and thread
        self.audio_capture_worker = AudioCaptureWorker(
            duration=self.duration, 
            fs=self.fs, 
            audio_queue=self.audio_queue
        )
        self.audio_capture_worker_thread = QThread()
        self.audio_capture_worker.moveToThread(self.audio_capture_worker_thread)
        self.audio_capture_worker_thread.started.connect(self.audio_capture_worker.run)
        self.audio_capture_worker.finished.connect(self.audio_capture_worker_thread.quit)
        self.audio_capture_worker.finished.connect(self.audio_capture_worker_thread.deleteLater)
        
        # Audio processor worker and thread
        self.audio_processor_worker = AudioProcessorWorker(
            fs=self.fs,
            parent=self,
            model=self.model, 
            processor=self.processor, 
            feature_extractor=self.feature_extractor, 
            audio_queue=self.audio_queue
        )
        self.audio_processor_worker_thread = QThread()
        self.audio_processor_worker.moveToThread(self.audio_processor_worker_thread)
        self.audio_processor_worker_thread.started.connect(self.audio_processor_worker.run)
        self.audio_processor_worker.finished.connect(self.audio_processor_worker_thread.quit)
        self.audio_processor_worker.finished.connect(self.audio_processor_worker_thread.deleteLater)

        if self.engine.app.settings["stt_enabled"]:
            self.listen()

    @property
    def device(self):
        return torch.device("cuda" if self.use_cuda else "cpu")
    
    @property
    def use_cuda(self):
        #return self.engine.app.settings["speech_to_text"]["use_cuda"] and torch.cuda.is_available()
        return torch.cuda.is_available()

    def load_whisper_model(self):
        self.logger.info("Loading model")
        model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-tiny.en").to(self.device)
        processor = AutoProcessor.from_pretrained("openai/whisper-tiny.en")
        feature_extractor = AutoFeatureExtractor.from_pretrained("openai/whisper-base")
        return model, processor, feature_extractor

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
        # strip whitespace
        transcription = transcription.strip()
        print("transcription: ", transcription)
        # check if transcription is empty or contains a single word
        if len(transcription) == 0 or len(transcription.split(" ")) == 1:
            return None
        return transcription

    def stop(self):
        self.stop_listening()
        self.audio_processor_worker.stop()
    
    def stop_listening(self):
        self.move_to_cpu()
        self.audio_capture_worker.stop_listening()

    def start_listening(self):
        self.move_to_gpu()
        self.audio_capture_worker.start_listening()

    def listen(self):
        """
        This function will listen for audio and convert it to text.
        It triggers the hear_signal which is connected to the engine.hear function.
        """
        self.logger.info("Listening")
        self.start_listening()
        self.audio_capture_worker_thread.start()
        self.audio_processor_worker_thread.start()
        # self.audio_capture_worker_thread.wait()
        # self.audio_processor_worker_thread.wait()
        self.move_to_cpu()