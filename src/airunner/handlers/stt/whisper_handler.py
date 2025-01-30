import os
import threading

import numpy as np
import torch
from transformers.models.whisper.modeling_whisper import WhisperForConditionalGeneration
from transformers.models.whisper.processing_whisper import WhisperProcessor
from transformers.models.whisper.feature_extraction_whisper import WhisperFeatureExtractor

from airunner.handlers.base_handler import BaseHandler
from airunner.enums import SignalCode, ModelType, ModelStatus
from airunner.exceptions import NaNException
from airunner.utils.clear_memory import clear_memory


class WhisperHandler(BaseHandler):
    """
    Handler for the Whisper model from OpenAI.
    """
    def __init__(self, *args, **kwargs):
        self.model_type = ModelType.STT
        self.model_class = "stt"
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()
        self._model = None
        self._processor = None
        self._feature_extractor = None
        self._fs = 16000

    @property
    def dtype(self):
        return torch.bfloat16

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
        file_path = os.path.expanduser(os.path.join(
            self.path_settings.base_path,
            "text",
            "models",
            "stt",
            "openai",
            "whisper-tiny"
        ))
        return os.path.abspath(file_path)

    def process_audio(self, audio_data):
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

    def load(self, retry:bool = False):
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
            self._model is not None and
            self._processor is not None and
            self._feature_extractor is not None
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
        self.logger.debug(f"Loading model from {self.model_path} to device {self.device}")
        device = self.device
        try:
            self._model = WhisperForConditionalGeneration.from_pretrained(
                self.model_path,
                local_files_only=True,
                torch_dtype=self.dtype,
                use_safetensors=True,
                force_download=False
            )
            self._model.to(device)
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            return None

    def _load_processor(self):
        model_path = self.model_path
        self.logger.debug(f"Loading processor from {model_path}")
        try:
            self._processor = WhisperProcessor.from_pretrained(
                model_path,
                local_files_only=True,
                torch_dtype=self.dtype,
                device_map=self.device
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
                local_files_only=True,
                torch_dtype=self.dtype,
                device_map=self.device
            )
        except Exception as e:
            self.logger.error(f"Failed to load feature extractor")
            self.logger.error(e)
            return None

    def _unload_model(self):
        del self._model
        self._model = None
        clear_memory(self.device)

    def _unload_processor(self):
        del self._processor
        self._processor = None
        clear_memory(self.device)

    def _unload_feature_extractor(self):
        del self._feature_extractor
        self._feature_extractor = None
        clear_memory(self.device)

    def _process_inputs(self, inputs: np.ndarray) -> str:
        if not self._feature_extractor:
            return ""
        inputs = torch.from_numpy(inputs).to(torch.float32).to(self.device)

        if torch.isnan(inputs).any():
            raise NaNException

        # Move inputs to CPU and ensure they are in float32 before passing to _feature_extractor
        inputs = inputs.cpu().to(torch.float32)
        inputs = self._feature_extractor(inputs, sampling_rate=self._fs, return_tensors="pt")

        if torch.isnan(inputs.input_features).any():
            raise NaNException

        inputs["input_features"] = inputs["input_features"].to(self.dtype).to(self.device)
        if torch.isnan(inputs.input_features).any():
            raise NaNException

        transcription = self._run(inputs)
        if transcription is None or 'nan' in transcription:
            raise NaNException

        return transcription

    def _run(
        self,
        inputs
    ) -> str:
        """
        Run the model on the given inputs.
        :param inputs: str - The transcription of the audio data.
        :param role: LLMChatRole - The role of the speaker.
        :return:
        """
        # Extract the tensor from the BatchFeature object
        self.logger.debug("Running model")
        try:
            input_tensor = inputs.input_values
        except AttributeError:
            input_tensor = inputs.input_features

        if torch.isnan(input_tensor).any():
            raise NaNException

        input_features = inputs.input_features
        if torch.isnan(input_features).any():
            raise NaNException

        data = dict(
            input_features=input_features,
            is_multilingual=self.whisper_settings.is_multilingual,
            temperature=self.whisper_settings.temperature,
            compression_ratio_threshold=self.whisper_settings.compression_ratio_threshold,
            logprob_threshold=self.whisper_settings.logprob_threshold,
            no_speech_threshold=self.whisper_settings.no_speech_threshold,
            time_precision=self.whisper_settings.time_precision,
        )

        if self.whisper_settings.is_multilingual:
            data["language"] = self.whisper_settings.language
            data["task"] = self.whisper_settings.task

        try:
            generated_ids = self._model.generate(
                **data
                # generation_config=None,
                # logits_processor=None,
                # stopping_criteria=None,
                # prefix_allowed_tokens_fn=None,
                # synced_gpus=True,
                # return_timestamps=None,
                # task="transcribe",
                # language="en",
                # prompt_ids=None,
                # prompt_condition_type=None,
                # condition_on_prev_tokens=None,
                # num_segment_frames=None,
                # attention_mask=None,
                # return_token_timestamps=None,
                # return_segments=False,
                # return_dict_in_generate=None,
            )
        except RuntimeError as e:
            generated_ids = None
            self.logger.error(f"Error in model generation: {e}")

        if generated_ids is None:
            return ""

        if torch.isnan(generated_ids).any():
            raise NaNException

        transcription = self.process_transcription(generated_ids)
        if len(transcription) == 0 or len(transcription.split(" ")) == 1:
            return ""

        return transcription

    def _send_transcription(self, transcription: str):
        """
        Emit the transcription so that other handlers can use it
        """
        self.emit_signal(SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL, {
            "transcription": transcription
        })

    def process_transcription(self, generated_ids) -> str:
        # Decode the generated ids
        generated_ids = generated_ids.to("cpu").to(torch.float32)
        transcription = self._processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]

        # Remove leading and trailing whitespace
        transcription = transcription.strip()

        # Remove any extra whitespace
        transcription = " ".join(transcription.split())

        return transcription
