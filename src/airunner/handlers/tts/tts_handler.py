from abc import abstractmethod
from typing import Optional, Type, ClassVar

from transformers import PreTrainedModel, ProcessorMixin

from airunner.handlers.base_handler import BaseHandler
from airunner.enums import ModelType
from airunner.utils.text_preprocessing import prepare_text_for_tts


class TTSHandler(BaseHandler):
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
    def interrupt_process_signal(self):
        """Signal to interrupt the current TTS process."""
        pass
    
    @abstractmethod
    def offload_to_cpu(self):
        """Move model to CPU to free up GPU memory."""
        pass
    
    @abstractmethod
    def move_to_device(self, device=None):
        """Move model to the specified device."""
        pass

    @abstractmethod
    def generate(self, message):
        """Generate speech from text."""
        pass

    @staticmethod
    def _prepare_text(text: str) -> str:
        """Prepare text for TTS processing using utility functions."""
        return prepare_text_for_tts(text)
