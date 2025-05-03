import os
import threading
import sounddevice as sd
import librosa

import numpy as np
import torch
from transformers.models.whisper.modeling_whisper import (
    WhisperForConditionalGeneration,
)
from transformers.models.whisper.processing_whisper import WhisperProcessor
from transformers.models.whisper.feature_extraction_whisper import (
    WhisperFeatureExtractor,
)

from airunner.handlers.base_model_manager import BaseModelManager
from airunner.enums import SignalCode, ModelType, ModelStatus
from airunner.exceptions import NaNException
from airunner.utils.memory import clear_memory
from airunner.settings import (
    AIRUNNER_DEFAULT_STT_HF_PATH,
    AIRUNNER_LOCAL_FILES_ONLY,
)


class WhisperModelManager(BaseModelManager):
    """
    Handler for the Whisper model from OpenAI.
    """

    def __init__(self, *args, **kwargs):
        self.model_type = ModelType.STT
        self.model_class = "stt"
        self._model_status = {
            ModelType.STT: ModelStatus.UNLOADED,
            ModelType.STT_PROCESSOR: ModelStatus.UNLOADED,
            ModelType.STT_FEATURE_EXTRACTOR: ModelStatus.UNLOADED,
        }
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()
        self._model = None
        self._processor = None
        self._feature_extractor = None
        self._sampling_rate = 16000
        self.audio_stream = None

        # Determine device map strategy based on available hardware
        self._device_map = "auto" if torch.cuda.is_available() else None

    @property
    def dtype(self):
        return torch.float16 if torch.cuda.is_available() else torch.float32

    @property
    def stt_is_loading(self):
        return self.model_status is ModelStatus.LOADING

    @property
    def stt_is_loaded(self):
        return self.model_status is ModelStatus.LOADED

    @property
    def stt_is_unloaded(self):
        return self.model_status is ModelStatus.UNLOADED

    @property
    def model_path(self) -> str:
        file_path = os.path.expanduser(
            os.path.join(
                self.path_settings.stt_model_path, AIRUNNER_DEFAULT_STT_HF_PATH
            )
        )
        return os.path.abspath(file_path)

    def process_audio(self, audio_data):
        """
        Process incoming audio data.
        """
        with self._lock:
            item = audio_data["item"]

            # Convert the byte string to a float32 array
            inputs = np.frombuffer(item, dtype=np.int16)
            inputs = inputs.astype(np.float32) / 32767.0

            transcription = None
            try:
                transcription = self._process_inputs(inputs)
            except Exception as e:
                self.logger.error(f"Failed to process inputs {e}")
                self.logger.error(e)

            if transcription:
                self._send_transcription(transcription)

    def load(self, retry: bool = False):
        if self.stt_is_loading or self.stt_is_loaded:
            return
        self.logger.debug("Loading Whisper (text-to-speech)")
        self.unload()
        self.change_model_status(ModelType.STT, ModelStatus.LOADING)
        self._load_model()
        # unsure why this is failing to load occasionally - this is a hack
        if self._model is None and retry is False:
            return self.load(retry=True)
        self._load_processor()
        self._load_feature_extractor()
        if (
            self._model is not None
            and self._processor is not None
            and self._feature_extractor is not None
        ):
            self.change_model_status(ModelType.STT, ModelStatus.LOADED)
            return True
        else:
            self.change_model_status(ModelType.STT, ModelStatus.FAILED)
            return False

    def unload(self):
        if self.stt_is_loading or self.stt_is_unloaded:
            return
        self.logger.debug("Unloading Whisper (text-to-speech)")
        self.change_model_status(ModelType.STT, ModelStatus.LOADING)
        self._unload_model()
        self._unload_processor()
        self._unload_feature_extractor()
        self.change_model_status(ModelType.STT, ModelStatus.UNLOADED)

    def _load_model(self):
        self.logger.debug(
            f"Loading model from {self.model_path} with device_map={self._device_map}"
        )
        try:
            # Clean up any GPU memory before loading to avoid conflicts
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # Handle different loading scenarios based on available hardware
            if torch.cuda.is_available():
                # For CUDA, use device_map="auto" with low_cpu_mem_usage=True
                self._model = WhisperForConditionalGeneration.from_pretrained(
                    self.model_path,
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                    torch_dtype=self.dtype,
                    use_safetensors=True,
                    force_download=False,
                    device_map=self._device_map,
                    low_cpu_mem_usage=True,  # Fix for meta tensor issues
                )
            else:
                # For CPU, load without device_map and with CPU optimization
                self._model = WhisperForConditionalGeneration.from_pretrained(
                    self.model_path,
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                    torch_dtype=self.dtype,
                    use_safetensors=True,
                    force_download=False,
                    low_cpu_mem_usage=True,  # Fix for meta tensor issues
                )
                # Explicitly move to CPU in case it's needed
                self._model = self._model.cpu()

        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            self.change_model_status(ModelType.STT, ModelStatus.FAILED)
            return None

    def _load_processor(self):
        model_path = self.model_path
        self.logger.debug(f"Loading processor from {model_path}")
        try:
            self._processor = WhisperProcessor.from_pretrained(
                model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            )
        except Exception as e:
            self.logger.error(f"Failed to load processor: {e}")
            return None

    def _load_feature_extractor(self):
        model_path = self.model_path
        self.logger.debug(f"Loading feature extractor {model_path}")
        try:
            self._feature_extractor = WhisperFeatureExtractor.from_pretrained(
                model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            )
        except Exception as e:
            self.logger.error(f"Failed to load feature extractor")
            self.logger.error(e)
            return None

    def _unload_model(self):
        del self._model
        self._model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _unload_processor(self):
        del self._processor
        self._processor = None

    def _unload_feature_extractor(self):
        del self._feature_extractor
        self._feature_extractor = None

    def _process_inputs(self, inputs: np.ndarray) -> str:
        """Process audio input array and return transcription"""
        if not self._feature_extractor or not self._model:
            return ""

        try:
            # Pre-process the audio on CPU first
            self.logger.debug("Processing audio input")

            # Convert numpy array to proper format
            input_features = self._feature_extractor(
                inputs, sampling_rate=self._sampling_rate, return_tensors="pt"
            ).input_features

            if torch.isnan(input_features).any():
                raise NaNException("NaN values found in input features")

            # Find model's device for placing tensors
            model_device = next(self._model.parameters()).device

            # Place features on the same device as model with correct dtype
            input_features = input_features.to(
                device=model_device, dtype=self.dtype
            )

            self.logger.debug(
                f"Input features prepared on device: {input_features.device}"
            )

            # Call the model directly with the features
            with torch.no_grad():
                # Pass only the necessary arguments
                result = self._model.generate(
                    input_features=input_features,
                    do_sample=True,
                    temperature=self.whisper_settings.temperature,
                    num_beams=1,
                )

            # Process the results
            transcription = self.process_transcription(result)

            if not transcription or "nan" in transcription:
                return ""

            return transcription

        except RuntimeError as e:
            self.logger.error(f"RuntimeError in audio processing: {e}")
            if "device" in str(e).lower():
                self.logger.error(
                    f"Device mismatch detected. Model on: {model_device}"
                )
            return ""
        except Exception as e:
            self.logger.error(f"Error in audio processing: {e}")
            return ""

    def _send_transcription(self, transcription: str):
        """
        Emit the transcription so that other handlers can use it
        """
        self.emit_signal(
            SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL,
            {"transcription": transcription},
        )

    def process_transcription(self, generated_ids) -> str:
        # Move to CPU only for decoding
        generated_ids_cpu = generated_ids.cpu()
        transcription = self._processor.batch_decode(
            generated_ids_cpu, skip_special_tokens=True
        )[0]

        # Remove leading and trailing whitespace
        transcription = transcription.strip()

        # Remove any extra whitespace
        transcription = " ".join(transcription.split())

        return transcription
