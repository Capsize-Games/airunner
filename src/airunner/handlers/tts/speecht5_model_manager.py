import os
import time
from queue import Queue
from typing import Optional, Union, ClassVar, Type, Dict, Any

import torch
import datasets
from datasets import (
    load_dataset,
    DatasetDict,
    Dataset,
    IterableDatasetDict,
    IterableDataset,
)
from transformers import (
    AutoTokenizer,
    PreTrainedModel,
    ProcessorMixin,
    SpeechT5Processor,
    SpeechT5ForTextToSpeech,
    SpeechT5HifiGan,
)

from airunner.handlers.tts.tts_model_manager import TTSModelManager
from airunner.enums import ModelType, ModelStatus, SpeechT5Voices
from airunner.handlers.tts.tts_request import TTSRequest
from airunner.utils.memory import clear_memory
from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY


class SpeechT5ModelManager(TTSModelManager):
    """
    SpeechT5 implementation of the TTSModelManager.
    Uses the SpeechT5ForTextToSpeech model and SpeechT5Processor.
    """

    target_model: ClassVar[str] = "microsoft/speecht5_tts"
    model_class: ClassVar[Type[PreTrainedModel]] = SpeechT5ForTextToSpeech
    processor_class: ClassVar[Type[ProcessorMixin]] = SpeechT5Processor
    vocoder_class: ClassVar[Type[PreTrainedModel]] = SpeechT5HifiGan
    tokenizer_class: ClassVar[Type[AutoTokenizer]] = AutoTokenizer
    speakers: Dict[str, str] = {
        SpeechT5Voices.US_MALE.value: "bdl",
        SpeechT5Voices.US_MALE_2.value: "rms",
        SpeechT5Voices.US_FEMALE.value: "slt",
        SpeechT5Voices.US_FEMALE_2.value: "clb",
        SpeechT5Voices.CANADIAN_MALE.value: "jmk",
        SpeechT5Voices.SCOTTISH_MALE.value: "awb",
        SpeechT5Voices.INDIAN_MALE.value: "ksp",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vocoder = None
        self._character_replacement_map = {"\n": " ", "’": "'", "-": " "}
        self._model: Optional[Type[PreTrainedModel]] = None
        self._vocoder: Optional[Type[PreTrainedModel]] = None
        self._processor: Optional[Type[ProcessorMixin]] = None
        self._tokenizer: Optional[Type[AutoTokenizer]] = None
        self._text_queue = Queue()
        self._speaker_embeddings = None
        self._dataset = None
        self._sentences = []
        self._do_interrupt = False
        self._cancel_generated_speech = False
        self._paused = False

    @property
    def status(self) -> ModelStatus:
        return self.model_status.get(ModelType.TTS, ModelStatus.UNLOADED)

    @property
    def speaker_embeddings_path(self) -> str:
        return os.path.join(
            self.path_settings.tts_model_path,
            "datasets/w4ffl35/speecht5_speaker_embeddings/speaker_embeddings",
        )

    @property
    def model(self) -> Type[PreTrainedModel]:
        return self._model

    @model.setter
    def model(self, value: Type[PreTrainedModel]):
        self._model = value

    @property
    def processor_path(self) -> str:
        return self.tts_path(self.speech_t5_settings.processor_path)

    @property
    def model_path(self) -> str:
        return self.tts_path(self.speech_t5_settings.model_path)

    @property
    def vocoder_path(self) -> str:
        return self.tts_path(self.speech_t5_settings.vocoder_path)

    @property
    def dtype(self) -> torch.dtype:
        return torch.float16

    @property
    def vocoder(self) -> Optional[Type[PreTrainedModel]]:
        return self._vocoder

    @vocoder.setter
    def vocoder(self, value: Optional[Type[PreTrainedModel]]):
        self._vocoder = value

    @property
    def processor(self) -> Optional[Type[ProcessorMixin]]:
        return self._processor

    @processor.setter
    def processor(self, value: Optional[Type[ProcessorMixin]]):
        self._processor = value

    @property
    def tokenizer(self) -> Optional[Type[AutoTokenizer]]:
        return self._tokenizer

    @tokenizer.setter
    def tokenizer(self, value: Optional[Type[AutoTokenizer]]):
        self._tokenizer = value

    @property
    def device(self) -> torch.device:
        """Return the appropriate device based on settings."""
        return torch.device("cuda" if self.use_cuda else "cpu")

    @property
    def torch_dtype(self) -> torch.dtype:
        """Return the consistent torch dtype to use across models and inputs."""
        return torch.float16 if self.use_cuda else torch.float32

    def tts_path(self, path: str) -> str:
        return os.path.join(self.path_settings.tts_model_path, path)

    # Refactored status methods for consistency
    def _set_status_unloaded(self):
        self.change_model_status(ModelType.TTS, ModelStatus.UNLOADED)

    def _set_status_loading(self):
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)

    def _set_status_loaded(self):
        self.change_model_status(ModelType.TTS, ModelStatus.LOADED)

    def _set_status_failed(self):
        self.change_model_status(ModelType.TTS, ModelStatus.FAILED)

    # Refactored load/unload methods for better error handling
    def load(self, target_model=None):
        if self.status is ModelStatus.LOADING:
            return
        if self.status in (
            ModelStatus.LOADED,
            ModelStatus.READY,
            ModelStatus.FAILED,
        ):
            self.unload()
        self.logger.debug(f"Loading text-to-speech")
        self._set_status_loading()
        self._load_model()
        self._load_vocoder()
        self._load_processor()
        self._load_speaker_embeddings()
        self._load_tokenizer()
        if (
            self.model is not None
            and self.vocoder is not None
            and self.processor is not None
            and self._speaker_embeddings is not None
            and self.tokenizer is not None
        ):
            # Explicitly move model and vocoder to the target device and dtype
            try:
                if self.model:
                    self.logger.debug(
                        f"Moving main model to device: {self.device} and dtype: {self.torch_dtype}"
                    )
                    self.model.to(self.device)
                    for param in self.model.parameters():
                        param.data = param.data.to(dtype=self.torch_dtype)
                if self.vocoder:
                    self.logger.debug(
                        f"Moving vocoder to device: {self.device} and dtype: {self.torch_dtype}"
                    )
                    self.vocoder.to(self.device)
                    for param in self.vocoder.parameters():
                        param.data = param.data.to(dtype=self.torch_dtype)
                self._set_status_loaded()
                self.logger.info("SpeechT5 models loaded successfully.")
            except Exception as e:
                self.logger.error(
                    f"Failed to move models to device {self.device}: {e}"
                )
                self._set_status_failed()
        else:
            self.logger.error(
                "Failed to load one or more SpeechT5 components."
            )
            self._set_status_failed()

    def unload(self):
        if self.status is ModelStatus.LOADING:
            return
        self._set_status_loading()
        self.model = None
        self.processor = None
        self.vocoder = None
        self._unload_speaker_embeddings()
        self.tokenizer = None
        clear_memory(self.memory_settings.default_gpu_tts)
        self._set_status_unloaded()

    def generate(self, tts_request: Type[TTSRequest]):
        if self.status is not ModelStatus.LOADED:
            return None
        if self._do_interrupt or self._paused:
            return None
        try:
            return self._do_generate(tts_request)
        except torch.cuda.OutOfMemoryError:
            self.logger.error("Out of memory")
            return None

    def _load_model(self):
        if self.model_class is None:
            return
        self.logger.debug(f"Loading model {self.model_path}")
        try:
            self.model = self.model_class.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                torch_dtype=self.torch_dtype,
                # Removed incorrect device_map argument
                # device_map=self.device,
            )
            self.logger.debug("Main model loaded.")
        except Exception as e:  # Catch broader exceptions during loading
            self.logger.error(f"Failed to load model: {e}")
            self.model = None  # Ensure model is None on failure

    def _load_tokenizer(self):
        self.logger.debug("Loading tokenizer")
        try:
            self.tokenizer = self.tokenizer_class.from_pretrained(
                self.model_path,  # Correctly uses model_path for SpeechT5 tokenizer
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                trust_remote_code=False,
                # Removed potentially incorrect arguments
                # device_map=self.device,
                # torch_dtype=self.torch_dtype,
            )
            self.logger.debug("Tokenizer loaded.")
        except Exception as e:
            self.logger.error(f"Failed to load tokenizer: {e}")
            self.tokenizer = None  # Ensure tokenizer is None on failure

    def _load_vocoder(self):
        self.logger.debug(f"Loading Vocoder {self.vocoder_path}")
        try:
            self.vocoder = self.vocoder_class.from_pretrained(
                self.vocoder_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                torch_dtype=self.torch_dtype,
                # Removed incorrect device_map argument
                # device_map=self.device,
            )
            self.logger.debug("Vocoder loaded.")
        except Exception as e:
            self.logger.error(f"Failed to load vocoder: {e}")
            self.vocoder = None  # Ensure vocoder is None on failure

    def _load_processor(self):
        self.logger.debug("Loading Processor")
        if self.processor_class:
            try:
                self.processor = self.processor_class.from_pretrained(
                    self.processor_path,
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                    # Removed potentially incorrect arguments
                    # torch_dtype=self.torch_dtype,
                    # device_map=self.device,
                )
                self.logger.debug("Processor loaded.")
            except Exception as e:
                self.logger.error(f"Failed to load processor: {e}")
                self.processor = None  # Ensure processor is None on failure
        else:
            self.processor = None

    def _load_speaker_embeddings(self):
        self.logger.debug("Loading speaker embeddings...")
        try:
            # Correctly load the embeddings file
            embeddings_path = self.speaker_embeddings_path
            if not os.path.exists(embeddings_path):
                self.logger.error(
                    f"Speaker embeddings file not found at: {embeddings_path}"
                )
                self._speaker_embeddings = None
                return

            self._speaker_embeddings = torch.load(embeddings_path)
            if self.use_cuda and self._speaker_embeddings is not None:
                # Move embeddings to CUDA device with appropriate dtype
                self._speaker_embeddings = self._speaker_embeddings.to(
                    self.device
                ).to(self.torch_dtype)
                self.logger.debug("Speaker embeddings moved to CUDA.")
            elif self._speaker_embeddings is not None:
                # Ensure embeddings are on the correct device (CPU) and dtype
                self._speaker_embeddings = self._speaker_embeddings.to(
                    self.device
                ).to(self.torch_dtype)
                self.logger.debug("Speaker embeddings loaded to CPU.")

        except Exception as e:
            self.logger.error(
                f"Failed to load or process speaker embeddings: {e}"
            )
            self._speaker_embeddings = (
                None  # Ensure embeddings are None on failure
            )

    @staticmethod
    def _extract_speaker_key(filename):
        # Assuming filename format like 'speaker_id_utterance_id.wav' or similar
        # Adjust this logic based on the actual filename structure in the dataset
        parts = os.path.basename(filename).split("_")
        if len(parts) >= 3:
            return parts[2]  # Example: extract speaker id
        return None  # Or handle cases where the format doesn't match

    def _load_dataset_by_speaker_key(
        self,
        speaker_key: str,
        embeddings_dataset: Union[
            DatasetDict, Dataset, IterableDatasetDict, IterableDataset
        ] = None,
    ) -> Optional[torch.Tensor]:
        # This method seems designed to load a specific speaker's embedding from a dataset
        # It wasn't directly involved in the original error, but let's ensure it's correct
        if embeddings_dataset is None:
            self.logger.warning(
                "Embeddings dataset not provided to _load_dataset_by_speaker_key"
            )
            return None

        embeddings = None
        try:
            for entry in embeddings_dataset:
                # Ensure 'filename' and 'xvector' keys exist in the dataset entry
                if "filename" not in entry or "xvector" not in entry:
                    self.logger.warning(
                        f"Skipping dataset entry due to missing keys: {entry}"
                    )
                    continue

                extracted_speaker = self._extract_speaker_key(
                    entry["filename"]
                )
                if (
                    extracted_speaker is not None
                    and speaker_key == extracted_speaker
                ):
                    # Convert xvector to tensor and add batch dimension
                    embeddings = torch.tensor(entry["xvector"]).unsqueeze(0)
                    self.logger.debug(
                        f"Found embeddings for speaker key: {speaker_key}"
                    )
                    break  # Found the speaker, exit loop
            if embeddings is None:
                self.logger.warning(
                    f"Speaker key '{speaker_key}' not found in embeddings dataset."
                )
        except Exception as e:
            self.logger.error(f"Error processing embeddings dataset: {e}")
            return None

        return embeddings

    def reload_speaker_embeddings(self):
        self._unload_speaker_embeddings()
        self._load_speaker_embeddings()

    def _unload_speaker_embeddings(self):
        self._speaker_embeddings = None
        clear_memory(self.memory_settings.default_gpu_tts)

    def _do_generate(self, tts_request: Type[TTSRequest]):
        self.logger.debug("Generating text-to-speech with T5")
        text = self._prepare_text(tts_request.message)

        if text == "":
            return None

        self.logger.debug("Processing inputs...")

        inputs = self.processor(
            text=text,
            return_tensors="pt",
        )
        inputs = self._move_inputs_to_device(inputs)

        self.logger.debug("Generating speech...")
        start = time.time()

        # Use consistent device and dtype handling
        try:
            speaker_embeddings = self._speaker_embeddings.to(
                dtype=self.torch_dtype, device=self.device
            )
            vocoder = self.vocoder.to(self.torch_dtype).to(self.device)

            speech = self.model.generate(
                **inputs,
                speaker_embeddings=speaker_embeddings,
                vocoder=vocoder,
                max_length=100,
            )
        except Exception as e:
            self.logger.error(f"Failed to generate speech: {str(e)}")
            self._cancel_generated_speech = False
            return None

        if not self._cancel_generated_speech:
            self.logger.debug(
                f"Generated speech in {time.time() - start:.2f} seconds"
            )
            response = speech.cpu().float().numpy()
            return response
        if not self._do_interrupt:
            self.logger.debug(f"Skipping generated speech: {text}")
            self._cancel_generated_speech = False
        return None

    def _move_inputs_to_device(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Move input tensors to the appropriate device. Only cast dtype if tensor is floating point."""
        try:
            device = self.device
            dtype = self.torch_dtype
            for key in inputs:
                if isinstance(inputs[key], torch.Tensor):
                    if torch.is_floating_point(inputs[key]):
                        inputs[key] = inputs[key].to(
                            device=device, dtype=dtype
                        )
                    else:
                        inputs[key] = inputs[key].to(device=device)
                elif isinstance(inputs[key], dict):
                    for subkey in inputs[key]:
                        if isinstance(inputs[key][subkey], torch.Tensor):
                            if torch.is_floating_point(inputs[key][subkey]):
                                inputs[key][subkey] = inputs[key][subkey].to(
                                    device=device, dtype=dtype
                                )
                            else:
                                inputs[key][subkey] = inputs[key][subkey].to(
                                    device=device
                                )
        except Exception as e:
            self.logger.error(
                f"Failed to move inputs to device and dtype: {str(e)}"
            )
        return inputs

    def unblock_tts_generator_signal(self):
        self.logger.debug("Unblocking text-to-speech generation...")
        self._do_interrupt = False
        self._paused = False

    def interrupt_process_signal(self):
        self._do_interrupt = True
        self._cancel_generated_speech = False
        self._paused = True
        self._text_queue = Queue()

    def cleanup(self):
        """Clean up resources when the handler is no longer needed."""
        self.unload()
        self._text_queue = Queue()
        self._sentences = []
