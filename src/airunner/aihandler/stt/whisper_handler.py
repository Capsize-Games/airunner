import torch
from transformers import AutoProcessor, WhisperForConditionalGeneration, AutoFeatureExtractor
from airunner.aihandler.stt.stt_handler import STTHandler


class WhisperHandler(STTHandler):
    """
    Handler for the Whisper model from OpenAI.
    """
    def load_model(self):
        self.logger.debug("Loading model")
        try:
            self.model = WhisperForConditionalGeneration.from_pretrained(
                "openai/whisper-tiny.en",
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
        except OSError as _e:
            return self.load_model(local_files_only=True)
        except NotImplementedError as _e:
            self.logger.error("Failed to load model")
            self.logger.error(_e)
            return None

    def load_processor(self):
        self.logger.debug("Loading processor")
        try:
            self.processor = AutoProcessor.from_pretrained(
                "openai/whisper-tiny.en",
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
        except Exception as e:
            self.logger.error("Failed to load processor")
            self.logger.error(e)
            return None

    def load_feature_extractor(self):
        try:
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(
                "openai/whisper-base",
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
        except OSError as _e:
            self.logger.error("Failed to load extractor")
            return None
