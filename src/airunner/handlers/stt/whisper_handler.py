import os
import threading

import numpy as np
import torch
from transformers.models.whisper.modeling_whisper import WhisperForConditionalGeneration
from transformers.models.whisper.processing_whisper import WhisperProcessor
from transformers.models.whisper.feature_extraction_whisper import WhisperFeatureExtractor

from airunner.handlers.base_handler import BaseHandler
from airunner.enums import SignalCode, ModelType, ModelStatus, LLMChatRole
from airunner.exceptions import NaNException
from airunner.settings import DEFAULT_STT_HF_PATH
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
            try:
                transcription = self._process_inputs(inputs)
            except Exception as e:
                self.logger.error(f"Failed to process inputs {e}")
                self.logger.error(e)
            try:
                self._process_human_speech(transcription)
            except ValueError as e:
                self.logger.error(f"Failed to process audio {e}")

    def load(self):
        if self.stt_is_loading or self.stt_is_loaded:
            return
        self.logger.debug("Loading Whisper (text-to-speech)")
        self.unload()
        self.change_model_status(ModelType.STT, ModelStatus.LOADING)
        self._load_model()
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
        model_path = self.model_path
        self.logger.debug(f"Loading model from {model_path}")
        try:
            self._model = WhisperForConditionalGeneration.from_pretrained(
                model_path,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device,
                use_safetensors=True
            )
        except Exception as e:
            self.logger.error(f"Failed to load model")
            self.logger.error(e)
            return None

    def _load_processor(self):
        model_path = self.model_path
        self.logger.debug(f"Loading processor from {model_path}")
        try:
            self._processor = WhisperProcessor.from_pretrained(
                model_path,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
        except Exception as e:
            self.logger.error(f"Failed to load processor")
            self.logger.error(e)
            return None

    def _load_feature_extractor(self):
        model_path = self.model_path
        self.logger.debug(f"Loading feature extractor {model_path}")
        try:
            self._feature_extractor = WhisperFeatureExtractor.from_pretrained(
                model_path,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
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

    def _process_inputs(
        self,
        inputs: np.ndarray,
        role: LLMChatRole = LLMChatRole.HUMAN,
    ) -> str:
        inputs = torch.from_numpy(inputs)

        if torch.isnan(inputs).any():
            raise NaNException

        inputs = self._feature_extractor(inputs, sampling_rate=self._fs, return_tensors="pt")
        if torch.isnan(inputs.input_features).any():
            raise NaNException

        inputs["input_features"] = inputs["input_features"].to(torch.bfloat16)
        if torch.isnan(inputs.input_features).any():
            raise NaNException

        inputs = inputs.to(self._model.device)
        if torch.isnan(inputs.input_features).any():
            raise NaNException

        transcription = self._run(inputs, role)
        if transcription is None or 'nan' in transcription:
            raise NaNException

        return transcription

    def _process_human_speech(self, transcription: str = None):
        """
        Process the human speech.
        This method is called when the model has processed the human speech
        and the transcription is ready to be added to the chat history.
        This should only be used for human speech.
        :param transcription:
        :return:
        """
        if transcription == "":
            raise ValueError("Transcription is empty")
        self.logger.debug("Processing human speech")
        data = {
            "message": transcription,
            "role": LLMChatRole.HUMAN
        }
        self.emit_signal(
            SignalCode.ADD_CHATBOT_MESSAGE_SIGNAL,
            data
        )

    def _run(
        self,
        inputs,
        role: LLMChatRole = LLMChatRole.HUMAN,
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

        generated_ids = self._model.generate(
            input_features=input_features,
            # generation_config=None,
            # logits_processor=None,
            # stopping_criteria=None,
            # prefix_allowed_tokens_fn=None,
            # synced_gpus=True,
            # return_timestamps=None,
            # task="transcribe",
            # language="en",
            # is_multilingual=True,
            # prompt_ids=None,
            # prompt_condition_type=None,
            # condition_on_prev_tokens=None,
            temperature=0.8,
            # compression_ratio_threshold=None,
            # logprob_threshold=None,
            # no_speech_threshold=None,
            # num_segment_frames=None,
            # attention_mask=None,
            # time_precision=0.02,
            # return_token_timestamps=None,
            # return_segments=False,
            # return_dict_in_generate=None,
        )
        if torch.isnan(generated_ids).any():
            raise NaNException

        transcription = self.process_transcription(generated_ids)
        if len(transcription) == 0 or len(transcription.split(" ")) == 1:
            return ""

        # Emit the transcription so that other handlers can use it
        self.emit_signal(SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL, {
            "transcription": transcription,
            "role": role
        })

        return transcription

    def process_transcription(self, generated_ids) -> str:
        # Decode the generated ids
        transcription = self._processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]

        # Remove leading and trailing whitespace
        transcription = transcription.strip()

        # Remove any extra whitespace
        transcription = " ".join(transcription.split())

        return transcription
