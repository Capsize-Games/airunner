from abc import abstractmethod, ABCMeta, ABC
from typing import Optional, Type, ClassVar

from transformers import PreTrainedModel, ProcessorMixin

from airunner.handlers.base_model_manager import BaseModelManager
from airunner.enums import ModelType, ModelStatus
from airunner.utils import prepare_text_for_tts
from airunner.handlers.tts.tts_request import TTSRequest

BaseModelManagerMeta = type(BaseModelManager)


class CombinedMeta(BaseModelManagerMeta, ABCMeta):
    """
    Combined metaclass for BaseModelManager and ABCMeta.
    """

    pass


class TTSModelManager(BaseModelManager, ABC, metaclass=CombinedMeta):
    """
    Abstract base class for text-to-speech handlers.
    Responsible for managing the model, processor, vocoder, and speaker embeddings.
    Use from a worker to avoid blocking the main thread.
    """

    # Class-wide properties defining model/processor classes
    target_model: ClassVar[Optional[str]] = None
    model_class: ClassVar[Optional[Type[PreTrainedModel]]] = None
    processor_class: ClassVar[Optional[Type[ProcessorMixin]]] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._model_status = {
            ModelType.TTS: ModelStatus.UNLOADED,
            ModelType.TTS_PROCESSOR: ModelStatus.UNLOADED,
            ModelType.TTS_FEATURE_EXTRACTOR: ModelStatus.UNLOADED,
            ModelType.TTS_VOCODER: ModelStatus.UNLOADED,
            ModelType.TTS_SPEAKER_EMBEDDINGS: ModelStatus.UNLOADED,
            ModelType.TTS_TOKENIZER: ModelStatus.UNLOADED,
        }
        self._tts_request: Optional[Type[TTSRequest]] = None
        self.model_type = ModelType.TTS
        self._engine = None

        # Runtime instances of the models
        self._model = None
        self._processor = None

    @property
    def tts_request(self) -> Optional[Type[TTSRequest]]:
        """
        The current TTS request.
        """
        return self._tts_request

    @tts_request.setter
    def tts_request(self, value: Optional[Type[TTSRequest]]):
        """
        Set the TTS request.
        """
        self._tts_request = value
        self._initialize()

    @property
    def message(self) -> str:
        if self.tts_request:
            return self.tts_request.message
        return ""

    @property
    def gender(self) -> str:
        if self.tts_request:
            return self.tts_request.gender
        return ""

    @abstractmethod
    def _initialize(self):
        """
        Initialize the TTS model and processor.
        """

    @abstractmethod
    def reload_speaker_embeddings(self):
        """
        Reload speaker embeddings.
        """

    @abstractmethod
    def interrupt_process_signal(self):
        """
        Signal to interrupt the current TTS process.
        """

    @abstractmethod
    def offload_to_cpu(self):
        """
        Move model to CPU to free up GPU memory.
        """

    @abstractmethod
    def move_to_device(self, device=None):
        """
        Move model to the specified device.
        """

    @abstractmethod
    def generate(self, message):
        """
        Generate speech from text.
        """

    @staticmethod
    def _prepare_text(text: str) -> str:
        """
        Prepare text for TTS processing using utility functions.
        """
        return prepare_text_for_tts(text)
