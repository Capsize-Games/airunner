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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = None
        self.processor = None
        self.feature_extractor = None
        self._model_status = ModelStatus.UNLOADED

    @property
    def model_path(self) -> str:
        path: str = self.path_settings.stt_model_path
        file_path = os.path.expanduser(os.path.join(path, DEFAULT_STT_HF_PATH))
        return os.path.abspath(file_path)

    def on_stt_load_signal(self):
        self.load()

    def on_stt_unload_signal(self):
        self.unload()

    def update_status(self, code: SignalCode, status: ModelStatus):
        pass

    def load(self):
        if self._model_status is ModelStatus.LOADING:
            return True
        self.unload()
        super().load()
        self.change_model_status(ModelType.STT, ModelStatus.LOADING)
        self._load_model()
        self._load_processor()
        self._load_feature_extractor()
        if (
            self.model is not None and
            self.processor is not None and
            self.feature_extractor is not None
        ):
            self.change_model_status(ModelType.STT, ModelStatus.LOADED)
            return True
        self.change_model_status(ModelType.STT, ModelStatus.FAILED)
        return False

    def unload(self):
        if self._model_status is ModelStatus.LOADING:
            return True
        super().unload()
        self.change_model_status(ModelType.STT, ModelStatus.LOADING)
        self.is_on_gpu = False
        self.unload_model()
        self.unload_processor()
        self.unload_feature_extractor()
        self.change_model_status(ModelType.STT, ModelStatus.UNLOADED)

    def _load_model(self):
        model_path = self.model_path
        self.logger.debug(f"Loading model from {model_path}")
        try:
            self.model = WhisperForConditionalGeneration.from_pretrained(
                model_path,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device,
                use_safetensors=True
            )
        except Exception as e:
            self.logger.error(f"Failed to load model")
            self.logger.error(e)
            return None

    def _load_processor(self):
        model_path = self.model_path
        self.logger.debug(f"Loading processor from {model_path}")
        try:
            self.processor = WhisperProcessor.from_pretrained(
                model_path,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
        except Exception as e:
            self.logger.error(f"Failed to load processor")
            self.logger.error(e)
            return None

    def _load_feature_extractor(self):
        model_path = self.model_path
        self.logger.debug(f"Loading feature extractor {model_path}")
        try:
            self.feature_extractor = WhisperFeatureExtractor.from_pretrained(
                model_path,
                local_files_only=True,
                torch_dtype=torch.bfloat16,
                device_map=self.device
            )
        except Exception as e:
            self.logger.error(f"Failed to load feature extractor")
            self.logger.error(e)
            return None

    def change_model_status(self, model: ModelType, status: ModelStatus):
        self._model_status = status
        super().change_model_status(model, status)
