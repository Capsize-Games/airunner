import torch
from transformers import (
    AutoProcessor,
    WhisperForConditionalGeneration,
    AutoFeatureExtractor
)
from airunner.aihandler.stt.stt_handler import STTHandler
from airunner.enums import SignalCode
from airunner.settings import DEFAULT_STT_HF_PATH
from airunner.utils.os_utils.get_full_file_path import get_full_file_path


class WhisperHandler(STTHandler):
    """
    Handler for the Whisper model from OpenAI.
    """
    def stop_capture(self):
        self.model = None
        self.processor = None
        self.feature_extractor = None
        super().stop_capture()
        self.emit_signal(SignalCode.TTS_MODEL_UNLOADED_SIGNAL)
        self.emit_signal(SignalCode.TTS_PROCESSOR_UNLOADED_SIGNAL)
        self.emit_signal(SignalCode.TTS_FEATURE_EXTRACTOR_UNLOADED_SIGNAL)

    def load_model(self):
        self.logger.debug(f"Loading model")
        self.model_path = get_full_file_path(
            file_name=DEFAULT_STT_HF_PATH,
            file_path=self.settings["path_settings"]["stt_model_path"],
            path_settings=self.settings["path_settings"],
            section="stt",
            logger=self.logger
        )
        try:
            val = WhisperForConditionalGeneration.from_pretrained(
                self.model_path,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
            self.emit_signal(SignalCode.TTS_MODEL_LOADED_SIGNAL, {
                "path": DEFAULT_STT_HF_PATH
            })
            return val
        except Exception as e:
            self.logger.error(f"Failed to load model")
            self.logger.error(e)
            self.emit_signal(SignalCode.TTS_MODEL_FAILED_SIGNAL, {
                "path": DEFAULT_STT_HF_PATH
            })
            return None

    def load_processor(self):
        self.logger.debug(f"Loading processor")
        self.model_path = get_full_file_path(
            file_name=DEFAULT_STT_HF_PATH,
            file_path=self.settings["path_settings"]["stt_model_path"],
            path_settings=self.settings["path_settings"],
            section="stt",
            logger=self.logger
        )
        try:
            val = AutoProcessor.from_pretrained(
                self.model_path,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
            self.emit_signal(SignalCode.TTS_MODEL_LOADED_SIGNAL, {
                "path": DEFAULT_STT_HF_PATH
            })
            return val
        except Exception as e:
            self.logger.error(f"Failed to load processor")
            self.logger.error(e)
            self.emit_signal(SignalCode.TTS_MODEL_FAILED_SIGNAL, {
                "path": DEFAULT_STT_HF_PATH
            })
            return None

    def load_feature_extractor(self):
        self.logger.debug(f"Loading feature extractor")
        self.model_path = get_full_file_path(
            file_name=DEFAULT_STT_HF_PATH,
            file_path=self.settings["path_settings"]["stt_model_path"],
            path_settings=self.settings["path_settings"],
            section="stt",
            logger=self.logger
        )
        try:
            val = AutoFeatureExtractor.from_pretrained(
                self.model_path,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
            self.emit_signal(SignalCode.TTS_MODEL_LOADED_SIGNAL, {
                "path": DEFAULT_STT_HF_PATH
            })
            return val
        except Exception as e:
            self.logger.error(f"Failed to load feature extractor")
            self.logger.error(e)
            self.emit_signal(SignalCode.TTS_MODEL_FAILED_SIGNAL, {
                "path": DEFAULT_STT_HF_PATH
            })
            return None
