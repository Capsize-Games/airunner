"""Service-owned base class for TTS runtime managers."""

from __future__ import annotations

import os
from typing import Any
from typing import Optional

from airunner_services.contract_enums import ModelStatus
from airunner_services.contract_enums import ModelType
from airunner_services.settings import AIRUNNER_BASE_PATH
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.database.models.application_settings import (
    ApplicationSettings,
)
from airunner_services.database.models.language_settings import (
    LanguageSettings,
)
from airunner_services.database.models.openvoice_settings import (
    OpenVoiceSettings,
)
from airunner_services.database.models.path_settings import PathSettings
from airunner_services.utils.application.api_reference import (
    peek_registered_api,
)
from airunner_services.utils.application.get_logger import get_logger
from airunner_services.utils.application.mediator_mixin import MediatorMixin
from airunner_services.utils.text.tts_preprocessing import (
    prepare_text_for_tts,
)


class TTSModelManager(MediatorMixin):
    """Provide service-owned runtime helpers shared by TTS managers."""

    target_model: Optional[str] = None
    model_class: Optional[type[Any]] = None
    processor_class: Optional[type[Any]] = None

    def __init__(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        self.signal_handlers = {}
        self.logger = get_logger(self.__class__.__name__, AIRUNNER_LOG_LEVEL)
        self._model_status = {
            ModelType.TTS: ModelStatus.UNLOADED,
            ModelType.TTS_PROCESSOR: ModelStatus.UNLOADED,
            ModelType.TTS_FEATURE_EXTRACTOR: ModelStatus.UNLOADED,
            ModelType.TTS_VOCODER: ModelStatus.UNLOADED,
            ModelType.TTS_SPEAKER_EMBEDDINGS: ModelStatus.UNLOADED,
            ModelType.TTS_TOKENIZER: ModelStatus.UNLOADED,
        }
        self._tts_request: Optional[object] = None
        self.model_type = ModelType.TTS
        self._engine = None
        self._model = None
        self._processor = None
        super().__init__(*args, **kwargs)

    def _load_settings(self, model_cls: type[Any]) -> Any:
        """Load one settings row, creating or defaulting when needed."""
        try:
            settings = model_cls.objects.first()
            if settings is not None:
                return settings
            settings = model_cls.objects.get_or_create()
            if settings is not None:
                return settings
        except Exception as exc:
            self.logger.debug(
                "Falling back to default %s settings: %s",
                model_cls.__name__,
                exc,
            )
        return model_cls()

    @property
    def application_settings(self) -> Any:
        """Return the persisted application settings or one default object."""
        return self._load_settings(ApplicationSettings)

    @property
    def language_settings(self) -> Any:
        """Return the persisted language settings or one default object."""
        return self._load_settings(LanguageSettings)

    @property
    def openvoice_settings(self) -> Any:
        """Return the persisted OpenVoice settings or one default object."""
        return self._load_settings(OpenVoiceSettings)

    @property
    def path_settings(self) -> Any:
        """Return the persisted path settings or one default object."""
        settings = self._load_settings(PathSettings)
        env_tts_model_path = os.environ.get("AIRUNNER_TTS_MODEL_PATH", "")
        if env_tts_model_path.strip():
            settings.tts_model_path = os.path.expanduser(env_tts_model_path)
            return settings
        if getattr(settings, "tts_model_path", None):
            return settings
        base_path = getattr(settings, "base_path", None) or AIRUNNER_BASE_PATH
        settings.tts_model_path = os.path.join(
            os.path.expanduser(base_path),
            "text/models/tts",
        )
        return settings

    def change_model_status(
        self,
        model: ModelType,
        status: ModelStatus,
    ) -> None:
        """Update local model status and notify the active API when present."""
        if model in self._model_status:
            self._model_status[model] = status
        else:
            self.logger.warning(
                "Attempted to set unknown model status %s=%s",
                model,
                status,
            )
            return

        api_ref = peek_registered_api()
        notify = getattr(api_ref, "change_model_status", None)
        if callable(notify):
            try:
                notify(model, status)
            except Exception:
                pass

    @property
    def tts_request(self) -> Optional[object]:
        """Return the current TTS request object."""
        return self._tts_request

    @property
    def model_status(self) -> dict[ModelType, ModelStatus]:
        """Return the per-component runtime status map."""
        return self._model_status

    @property
    def status(self) -> ModelStatus:
        """Return the primary TTS runtime status."""
        return self._model_status.get(ModelType.TTS, ModelStatus.UNLOADED)

    @tts_request.setter
    def tts_request(self, value: Optional[object]) -> None:
        """Set the current request and refresh manager state."""
        self._tts_request = value
        self._initialize()

    @property
    def message(self) -> str:
        """Return the current request text, if one exists."""
        if self.tts_request:
            return getattr(self.tts_request, "message", "")
        return ""

    @property
    def gender(self) -> str:
        """Return the current request gender, if one exists."""
        if self.tts_request:
            return getattr(self.tts_request, "gender", "")
        return ""

    @staticmethod
    def _prepare_text(text: str) -> str:
        """Normalize text before it is handed to a TTS backend."""
        return prepare_text_for_tts(text)

    def offload_to_cpu(self) -> None:
        """Default no-op hook for TTS backends that can offload state."""

    def move_to_device(self, device: Optional[object] = None) -> None:
        """Default no-op hook for TTS backends that support devices."""
        del device


__all__ = ["TTSModelManager"]
