import torch
from transformers import AutoProcessor, WhisperForConditionalGeneration, AutoFeatureExtractor
from airunner.aihandler.stt.stt_handler import STTHandler


class WhisperHandler(STTHandler):
    """
    Handler for the Whisper model from OpenAI.
    """
    def load_model(self, local_files_only=True):
        self.logger.debug("Loading model")
        try:
            self.model = WhisperForConditionalGeneration.from_pretrained(
                "openai/whisper-tiny.en",
                local_files_only=local_files_only,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
        except OSError as _e:
            return self.load_model(local_files_only=False)
        except NotImplementedError as _e:
            self.logger.error("Failed to load model")
            self.logger.error(_e)
            return None

    def load_processor(self, local_files_only=True):
        self.logger.debug("Loading processor")
        try:
            self.processor = AutoProcessor.from_pretrained(
                "openai/whisper-tiny.en",
                local_files_only=local_files_only,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
        except OSError as _e:
            return self.load_processor(local_files_only=False)
        except NotImplementedError as _e:
            self.logger.error("Failed to load processor")
            self.logger.error(_e)
            return None

    def load_feature_extractor(self, local_files_only=True):
        try:
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(
                "openai/whisper-base",
                local_files_only=local_files_only,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
        except OSError as _e:
            if local_files_only:
                return self.load_feature_extractor(local_files_only=False)
            else:
                self.logger.error("Failed to load extractor")
                return None
