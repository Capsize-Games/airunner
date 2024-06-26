import os
import torch
from transformers.models.whisper.modeling_whisper import WhisperForConditionalGeneration
from transformers.models.whisper.processing_whisper import WhisperProcessor
from transformers.models.whisper.feature_extraction_whisper import WhisperFeatureExtractor
from airunner.aihandler.stt.stt_handler import STTHandler
from airunner.enums import SignalCode, ModelType, ModelStatus
from airunner.settings import DEFAULT_STT_HF_PATH


class WhisperHandler(STTHandler):
    """
    Handler for the Whisper model from OpenAI.
    """
    def stop_capture(self, data: dict):
        self.unload()
        super().stop_capture(data)

    def update_status(self, code: SignalCode, status: ModelStatus):
        pass

    def load_model(self):
        self.logger.debug(f"Loading model")

        file_path = os.path.join(self.settings["path_settings"][f"stt_model_path"], DEFAULT_STT_HF_PATH)
        file_path = os.path.expanduser(file_path)
        file_path = os.path.abspath(file_path)
        self.change_model_status(ModelType.STT, ModelStatus.LOADING, file_path)
        try:
            val = WhisperForConditionalGeneration.from_pretrained(
                file_path,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
            self.change_model_status(ModelType.STT, ModelStatus.LOADED, file_path)
            return val
        except Exception as e:
            self.logger.error(f"Failed to load model")
            self.logger.error(e)
            self.change_model_status(ModelType.STT, ModelStatus.FAILED, file_path)
            return None

    def load_processor(self):
        self.logger.debug(f"Loading processor")
        file_path = os.path.join(self.settings["path_settings"][f"stt_model_path"], DEFAULT_STT_HF_PATH)
        file_path = os.path.expanduser(file_path)
        file_path = os.path.abspath(file_path)
        self.change_model_status(ModelType.STT_PROCESSOR, ModelStatus.LOADING, file_path)
        try:
            val = WhisperProcessor.from_pretrained(
                file_path,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
            self.change_model_status(ModelType.STT_PROCESSOR, ModelStatus.LOADED, file_path)
            return val
        except Exception as e:
            self.logger.error(f"Failed to load processor")
            self.logger.error(e)
            self.change_model_status(ModelType.STT_PROCESSOR, ModelStatus.FAILED, file_path)
            return None

    def load_feature_extractor(self):
        self.logger.debug(f"Loading feature extractor")
        file_path = os.path.join(self.settings["path_settings"][f"stt_model_path"], DEFAULT_STT_HF_PATH)
        file_path = os.path.expanduser(file_path)
        file_path = os.path.abspath(file_path)
        self.change_model_status(ModelType.STT_FEATURE_EXTRACTOR, ModelStatus.LOADING, file_path)
        try:
            val = WhisperFeatureExtractor.from_pretrained(
                file_path,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
            self.change_model_status(ModelType.STT_FEATURE_EXTRACTOR, ModelStatus.LOADED, file_path)
            return val
        except Exception as e:
            self.logger.error(f"Failed to load feature extractor")
            self.logger.error(e)
            self.change_model_status(ModelType.STT_FEATURE_EXTRACTOR, ModelStatus.FAILED, file_path)
            return None
