import threading
import torch
import numpy as np
from PySide6.QtCore import Slot
from transformers import AutoProcessor, WhisperForConditionalGeneration, AutoFeatureExtractor
from airunner.aihandler.base_handler import BaseHandler
from airunner.enums import SignalCode


class STTHandler(BaseHandler):
    listening = False

    def on_process_audio(self, message: dict):
        audio_data = message["audio_data"]
        with self.lock:
            fs = 16000
            # Convert the byte string to a float32 array
            inputs = np.frombuffer(audio_data, dtype=np.int16)
            inputs = inputs.astype(np.float32) / 32767.0

            # Convert numpy array to PyTorch tensor
            inputs = torch.from_numpy(inputs)

            # Extract features from the audio data
            inputs = self.feature_extractor(inputs, sampling_rate=fs, return_tensors="pt")

            # Convert inputs to BFloat16 if CUDA is available
            if self.use_cuda:
                inputs["input_features"] = inputs["input_features"].to(torch.bfloat16)

            # Move inputs to device
            inputs = inputs.to(self.model.device)

            # Run the model
            transcription = self.run(inputs)

            self.emit_signal(SignalCode.STT_AUDIO_PROCESSED, transcription)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = threading.Lock()
        self.model = None
        self.model = None
        self.processor = None
        self.feature_extractor = None
        self.model = None
        self.is_on_gpu = False
        self.load_model()
        self.load_processor()
        self.load_feature_extractor()
        self.register(SignalCode.STT_PROCESS_AUDIO_SIGNAL, self.on_process_audio)

    @property
    def use_cuda(self):
        return torch.cuda.is_available()

    def load_model(self, local_files_only=True):
        self.logger.debug("Loading model")
        try:
            self.model = WhisperForConditionalGeneration.from_pretrained(
                "openai/whisper-tiny.en",
                local_files_only=local_files_only,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
        except OSError as _e:
            return self.load_model(local_files_only=False)
        except NotImplementedError as _e:
            self.logger.error("Failed to load model")
            self.logger.error(_e)
            return None

    def load_processor(self, local_files_only=True):
        self.logger.debug("Loading processor")
        try:
            self.processor = AutoProcessor.from_pretrained(
                "openai/whisper-tiny.en",
                local_files_only=local_files_only,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
        except OSError as _e:
            return self.load_processor(local_files_only=False)
        except NotImplementedError as _e:
            self.logger.error("Failed to load processor")
            self.logger.error(_e)
            return None

    def load_feature_extractor(self, local_files_only=True):
        try:
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(
                "openai/whisper-base",
                local_files_only=local_files_only,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
        except OSError as _e:
            if local_files_only:
                return self.load_feature_extractor(local_files_only=False)
            else:
                self.logger.error("Failed to load extractor")
                return None

    def move_to_gpu(self):
        if not self.is_on_gpu:
            self.logger.debug("Moving model to GPU")
            self.model = self.model.to(self.device)
            self.processor = self.processor
            self.feature_extractor = self.feature_extractor
            self.is_on_gpu = True

    def move_inputs_to_device(self, inputs):
        if self.use_cuda:
            self.logger.debug("Moving inputs to CUDA")
            try:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            except AttributeError:
                pass
            inputs = inputs.to(torch.bfloat16)
        return inputs

    def run(self, inputs):
        self.logger.debug("Running model")
        input_features = inputs.input_features

        # Generate ids
        generated_ids = self.model.generate(input_features)

        # Decode the generated ids
        transcription = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        transcription = transcription.strip()

        if len(transcription) == 0 or len(transcription.split(" ")) == 1:
            return None

        self.emit_signal(SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL, transcription)
        return transcription
