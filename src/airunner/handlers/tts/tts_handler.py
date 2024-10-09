from airunner.handlers.base_handler import BaseHandler
from airunner.enums import ModelType


class TTSHandler(BaseHandler):
    """
    Generates speech from given text. 
    Responsible for managing the model, processor, vocoder, and speaker embeddings.
    Generates using either the SpeechT5 model.

    Use from a worker to avoid blocking the main thread.
    """
    target_model = None
    model_class_ = None
    processor_class_ = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_type = ModelType.TTS
        self.model_class = "tts"
        self._engine = None

    def interrupt_process_signal(self):
        pass
    
    def offload_to_cpu(self):
        pass
    
    def move_to_device(self, device=None):
        pass

    def load(self, target_model=None):
        pass

    def unload(self):
        pass

    def run(self):
        pass

    def initialize(self):
        pass

    def do_generate(self, message):
        pass

