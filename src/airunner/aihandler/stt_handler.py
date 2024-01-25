import torch
import numpy as np

from transformers import AutoProcessor, WhisperForConditionalGeneration, AutoFeatureExtractor

from airunner.aihandler.base_handler import BaseHandler

from PyQt6.QtCore import pyqtSignal

from airunner.aihandler.enums import SignalCode


class STTHandler(BaseHandler):
    listening = False
    move_to_cpu_signal = pyqtSignal()

    def on_process_audio(self, audio_data, fs):
        inputs = np.squeeze(audio_data)
        inputs = self.feature_extractor(inputs, sampling_rate=fs, return_tensors="pt")
        inputs = inputs.to(self.model.device)
        transcription = self.run(inputs)
        self.emit(SignalCode.STT_AUDIO_PROCESSED, transcription)

    def on_move_to_cpu(self):
        self.logger.info("Moving model to CPU")
        self.model = self.model.to("cpu")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_model()
        self.register(SignalCode.MOVE_TO_CPU_SIGNAL, self.on_move_to_cpu)
        self.register(SignalCode.PROCESS_AUDIO_SIGNAL, self.on_process_audio)

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
