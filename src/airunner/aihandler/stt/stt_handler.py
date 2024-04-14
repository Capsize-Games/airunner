import base64
import hashlib
import threading
from typing import Any

import torch
import numpy as np
from cryptography.fernet import Fernet

from airunner.aihandler.base_handler import BaseHandler
from airunner.enums import SignalCode


class STTHandler(BaseHandler):
    """
    Base class for all Speech-to-Text handlers.
    Override this class to implement a new Speech-to-Text handler.
    """
    listening = False

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
        self.model_type = "stt"
        self.fs = 16000

    @property
    def use_cuda(self):
        return torch.cuda.is_available()

    def on_process_audio(self, data: dict):
        audio_data = data["message"]
        with self.lock:
            # Convert the byte string to a float32 array
            inputs = np.frombuffer(audio_data, dtype=np.int16)
            inputs = inputs.astype(np.float32) / 32767.0

            # Convert numpy array to PyTorch tensor
            inputs = torch.from_numpy(inputs)

            # Extract features from the audio data
            inputs = self.feature_extractor(inputs, sampling_rate=self.fs, return_tensors="pt")

            # Convert inputs to BFloat16 if CUDA is available
            if self.use_cuda:
                inputs["input_features"] = inputs["input_features"].to(torch.bfloat16)

            # Move inputs to device
            inputs = inputs.to(self.model.device)

            # Run the model
            transcription = self.run(inputs)

            self.emit_signal(SignalCode.STT_AUDIO_PROCESSED, transcription)

    def load_model(self, local_files_only=True):
        pass

    def load_processor(self, local_files_only=True):
        pass

    def load_feature_extractor(self, local_files_only=True):
        pass

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

    def run(self, inputs) -> Any | None:
        """
        Run the model on the given inputs.
        :param inputs: str - The transcription of the audio data.
        :return:
        """
        self.logger.debug("Running model")
        input_features = inputs.input_features

        # Generate ids
        generated_ids = self.model.generate(input_features)

        transcription = self.process_transcription(generated_ids)

        if len(transcription) == 0 or len(transcription.split(" ")) == 1:
            return None

        # Emit the transcription so that other handlers can use it
        self.emit_signal(SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL, {
            "transcription": transcription
        })

        return transcription

    def process_transcription(self, generated_ids):
        # Decode the generated ids
        transcription = self.processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]

        # Remove leading and trailing whitespace
        transcription = transcription.strip()

        # Remove any extra whitespace
        transcription = " ".join(transcription.split())

        if False:
            transcription = self.encrypt_transcription(transcription)

        return transcription

    def encrypt_transcription(self, transcription):
        return transcription
