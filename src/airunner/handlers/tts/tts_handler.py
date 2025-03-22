from abc import abstractmethod, ABCMeta, ABC
from typing import Optional, Type, ClassVar

from transformers import PreTrainedModel, ProcessorMixin

from airunner.handlers.base_handler import BaseHandler
from airunner.enums import ModelType
from airunner.utils import prepare_text_for_tts


BaseHandlerMeta = type(BaseHandler)


class CombinedMeta(BaseHandlerMeta, ABCMeta):
    pass


class TTSHandler(BaseHandler, ABC, metaclass=CombinedMeta):
    """
    Abstract base class for text-to-speech handlers.
    Responsible for managing the model, processor, vocoder, and speaker embeddings.

    Use from a worker to avoid blocking the main thread.
    """
    # These should remain class attributes as they define class-wide properties
    # that identify which model/processor classes to use for this handler type
    target_model: ClassVar[Optional[str]] = None
    model_class: ClassVar[Optional[Type[PreTrainedModel]]] = None
    processor_class: ClassVar[Optional[Type[ProcessorMixin]]] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_type = ModelType.TTS
        self._engine = None
        
        # Runtime instances of the models should be instance attributes
        self._model = None
        self._processor = None
    
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
        """Prepare text for TTS processing using utility functions."""
        return prepare_text_for_tts(text)
