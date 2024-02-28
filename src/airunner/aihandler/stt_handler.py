import torch
import numpy as np

from transformers import AutoProcessor, WhisperForConditionalGeneration, AutoFeatureExtractor

from airunner.aihandler.base_handler import BaseHandler

from airunner.enums import SignalCode


class STTHandler(BaseHandler):
    listening = False

    def on_process_audio(self, audio_data: bytes):
        fs = 16000
        # Convert the byte string to a float32 array
        inputs = np.frombuffer(audio_data, dtype=np.int16)
        inputs = inputs.astype(np.float32) / 32767.0

        # Extract features from the audio data
        inputs = self.feature_extractor(inputs, sampling_rate=fs, return_tensors="pt")
        inputs = inputs.to(self.model.device)
        transcription = self.run(inputs)
        self.emit(SignalCode.STT_AUDIO_PROCESSED, transcription)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = None
        self.model = None
        self.processor = None
        self.feature_extractor = None
        self.model = None
        self.processor = None
        self.feature_extractor = None
        self.is_on_gpu = False
        self.load_model()
        self.register(SignalCode.STT_PROCESS_AUDIO_SIGNAL, self.on_process_audio)

    @property
    def device(self):
        return torch.device("cuda" if self.use_cuda else "cpu")
    
    @property
    def use_cuda(self):
        return torch.cuda.is_available()

    def load_model(self, local_files_only=True):
        self.logger.info("Loading model")
        try:
            self.model = WhisperForConditionalGeneration.from_pretrained(
                "openai/whisper-tiny.en",
                local_files_only=local_files_only
            ).to(
                self.device
            )
        except OSError as _e:
            return self.load_model(local_files_only=False)

        try:
            self.processor = AutoProcessor.from_pretrained(
                "openai/whisper-tiny.en",
                local_files_only=local_files_only
            )
        except OSError as _e:
            return self.load_model(local_files_only=False)

        try:
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(
                "openai/whisper-base",
                local_files_only=local_files_only
            )
        except OSError as _e:
            return self.load_model(local_files_only=False)

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
        if len(transcription) == 0 or len(transcription.split(" ")) == 1:
            return None
        self.emit(SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL, transcription)
        return transcription
