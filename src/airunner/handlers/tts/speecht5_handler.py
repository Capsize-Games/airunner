import os
import time
from abc import ABC
from queue import Queue
from typing import Optional, Union, ClassVar, Type, Dict, Any

import torch

import datasets
from datasets import (
    load_dataset, 
    DatasetDict, 
    Dataset, 
    IterableDatasetDict, 
    IterableDataset
)
from transformers import AutoTokenizer, PreTrainedModel, ProcessorMixin
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech
from transformers import SpeechT5HifiGan

from airunner.handlers.tts.tts_handler import TTSHandler
from airunner.enums import ModelType, ModelStatus, SpeechT5Voices
from airunner.utils.clear_memory import clear_memory


class SpeechT5Handler(TTSHandler, ABC):
    """
    SpeechT5 implementation of the TTSHandler.
    Uses the SpeechT5ForTextToSpeech model and SpeechT5Processor.
    """
    target_model: ClassVar[str] = "microsoft/speecht5_tts"
    model_class: ClassVar[Type[PreTrainedModel]] = SpeechT5ForTextToSpeech
    processor_class: ClassVar[Type[ProcessorMixin]] = SpeechT5Processor
    vocoder_class: ClassVar[Type[PreTrainedModel]] = SpeechT5HifiGan
    tokenizer_class: ClassVar[Type[AutoTokenizer]] = AutoTokenizer
    dataset_path: ClassVar[str] = "Matthijs/cmu-arctic-xvectors"
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
        self._character_replacement_map = {
            "\n": " ",
            "’": "'",
            "-": " "
        }
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
        return torch.device("cuda" if self.tts_settings.use_cuda else "cpu")
    
    @property
    def torch_dtype(self) -> torch.dtype:
        """Return the consistent torch dtype to use across models and inputs."""
        return torch.float16 if self.tts_settings.use_cuda else torch.float32

    def tts_path(self, path: str) -> str:
        return os.path.join(self.path_settings.tts_model_path, path)

    def _set_status_unloaded(self):
        self.change_model_status(ModelType.TTS, ModelStatus.UNLOADED)

    def _set_status_loading(self):
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
    
    def _set_status_loaded(self):
        self.change_model_status(ModelType.TTS, ModelStatus.LOADED)

    def _set_status_failed(self):
        self.change_model_status(ModelType.TTS, ModelStatus.FAILED)

    def generate(self, message: str):
        if self.model_status is not ModelStatus.LOADED:
            return None

        if self._do_interrupt or self._paused:
            return None

        try:
            return self._do_generate(message)
        except torch.cuda.OutOfMemoryError:
            self.logger.error("Out of memory")
            return None

    def load(self, target_model=None):
        if self.model_status is ModelStatus.LOADING:
            return
        if self.model_status in (
            ModelStatus.LOADED,
            ModelStatus.READY,
            ModelStatus.FAILED
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
            self._set_status_loaded()
        else:
            self._set_status_failed()

    def unload(self):
        if self.model_status is ModelStatus.LOADING:
            return
        self._set_status_loading()
        self.model = None
        self.processor = None
        self.vocoder = None
        self._unload_speaker_embeddings()
        self.tokenizer = None
        clear_memory(self.memory_settings.default_gpu_tts)
        self._set_status_unloaded()

    def _load_model(self):
        if self.model_class is None:
            return
        self.logger.debug(f"Loading model {self.model_path}")
        try:
            self.model = self.model_class.from_pretrained(
                self.model_path,
                local_files_only=True,
                torch_dtype=self.torch_dtype,
                device_map=self.device
            )
        except EnvironmentError as _e:
            self.logger.error(f"Failed to load model {_e}")

    def _load_tokenizer(self):
        self.logger.debug("Loading tokenizer")

        try:
            self.tokenizer = self.tokenizer_class.from_pretrained(
                self.model_path,
                device_map=self.device,
                torch_dtype=self.torch_dtype,
                local_files_only=True,
                trust_remote_code=False
            )
        except Exception as e:
            self.logger.error("Failed to load tokenizer")
            self.logger.error(e)

    def _load_vocoder(self):
        self.logger.debug(f"Loading Vocoder {self.vocoder_path}")
        try:
            self.vocoder = self.vocoder_class.from_pretrained(
                self.vocoder_path,
                local_files_only=True,
                torch_dtype=self.torch_dtype,
                device_map=self.device
            )
        except Exception as e:
            self.logger.error("Failed to load vocoder")
            self.logger.error(e)

    def _load_processor(self):
        self.logger.debug("Loading Procesor")
        if self.processor_class:
            try:
                self.processor = self.processor_class.from_pretrained(
                    self.processor_path,
                    local_files_only=True,
                    torch_dtype=self.torch_dtype,
                    device_map=self.device
                )
            except Exception as e:
                self.logger.error("Failed to load processor")
                self.logger.error(e)

    def _load_speaker_embeddings(self):
        self.logger.debug("Loading speaker embeddings...")
        embeddings_dataset = load_dataset(
            self.dataset_path, 
            split=datasets.Split.VALIDATION
        )
        speaker_key = self.speakers[self.speech_t5_settings.voice]
        embeddings = self._load_dataset_by_speaker_key(
            speaker_key,
            embeddings_dataset
        )
        if embeddings is None:
            self.logger.error(
                "Failed to load speaker embeddings. Using fallback"
            )
            embeddings = self._load_dataset_by_speaker_key(
                "slt",
                embeddings_dataset
            )

        self._speaker_embeddings = embeddings
        if self._speaker_embeddings is not None:
            if self.use_cuda:
                self.logger.info("Moving speaker embeddings to CUDA")
                self._speaker_embeddings = self._speaker_embeddings.to(
                    torch.bfloat16
                ).cuda()
        else:
            self.logger.error("Failed to load speaker embeddings")
        
    def _extract_speaker_key(self, filename):
        return filename.split("_")[2]

    def _load_dataset_by_speaker_key(
        self, 
        speaker_key: str,
        embeddings_dataset: Union[
            DatasetDict, 
            Dataset, 
            IterableDatasetDict, 
            IterableDataset
        ] = None
    ) -> Optional[torch.Tensor]:
        embeddings = None
        for entry in embeddings_dataset:
            speaker = self._extract_speaker_key(entry["filename"])
            if speaker_key == speaker:
                embeddings = torch.tensor(entry["xvector"]).unsqueeze(0)
                break
        return embeddings

    def reload_speaker_embeddings(self):
        self._unload_speaker_embeddings()
        self._load_speaker_embeddings()

    def _unload_speaker_embeddings(self):
        self._speaker_embeddings = None
        clear_memory(self.memory_settings.default_gpu_tts)

    def _do_generate(self, message: str):
        self.logger.debug("Generating text-to-speech with T5")
        text = self._prepare_text(message)

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
            speaker_embeddings = self._speaker_embeddings.to(self.torch_dtype).to(self.device)
            vocoder = self.vocoder.to(self.torch_dtype).to(self.device)
            
            speech = self.model.generate(
                **inputs,
                speaker_embeddings=speaker_embeddings,
                vocoder=vocoder,
                max_length=100
            )
        except Exception as e:
            self.logger.error(f"Failed to generate speech: {str(e)}")
            self._cancel_generated_speech = False
            return None

        if not self._cancel_generated_speech:
            self.logger.debug(f"Generated speech in {time.time() - start:.2f} seconds")
            response = speech.cpu().float().numpy()
            return response
        if not self._do_interrupt:
            self.logger.debug(f"Skipping generated speech: {text}")
            self._cancel_generated_speech = False
        return None

    def _move_inputs_to_device(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Move input tensors to the appropriate device."""
        try:
            device = self.device
            for key in inputs:
                if isinstance(inputs[key], torch.Tensor):
                    inputs[key] = inputs[key].to(device)
                elif isinstance(inputs[key], dict):
                    for subkey in inputs[key]:
                        if isinstance(inputs[key][subkey], torch.Tensor):
                            inputs[key][subkey] = inputs[key][subkey].to(device)
                            
        except Exception as e:
            self.logger.error(f"Failed to move inputs to device: {str(e)}")
            
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
