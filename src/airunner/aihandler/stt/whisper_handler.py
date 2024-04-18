import torch
from transformers import (
    AutoProcessor,
    WhisperForConditionalGeneration,
    AutoFeatureExtractor
)
from airunner.aihandler.stt.stt_handler import STTHandler
from airunner.settings import DEFAULT_STT_HF_PATH


class WhisperHandler(STTHandler):
    """
    Handler for the Whisper model from OpenAI.
    """
    def load_component(self, model_path, component_class, component_name):
        self.logger.debug(f"Loading {component_name}")
        try:
            return component_class.from_pretrained(
                model_path,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
        except Exception as e:
            self.logger.error(f"Failed to load {component_name}")
            self.logger.error(e)
            return None

    def load_model(self):
        self.model = self.load_component(DEFAULT_STT_HF_PATH, WhisperForConditionalGeneration, "model")

    def load_processor(self):
        self.processor = self.load_component(DEFAULT_STT_HF_PATH, AutoProcessor, "processor")

    def load_feature_extractor(self):
        self.feature_extractor = self.load_component(DEFAULT_STT_HF_PATH, AutoFeatureExtractor, "feature extractor")
