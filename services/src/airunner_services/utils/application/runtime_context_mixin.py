"""Service-owned runtime context helpers for shared non-GUI classes."""

from __future__ import annotations

from typing import Any, Optional, TypeVar

from airunner_services.contract_enums import SignalCode
from airunner_services.database.models.application_settings import (
    ApplicationSettings,
)
from airunner_services.database.models.chatbot import Chatbot
from airunner_services.database.models.controlnet_settings import (
    ControlnetSettings,
)
from airunner_services.database.models.espeak_settings import (
    EspeakSettings,
)
from airunner_services.database.models.generator_settings import (
    GeneratorSettings,
)
from airunner_services.database.models.language_settings import (
    LanguageSettings,
)
from airunner_services.database.models.llm_generator_settings import (
    LLMGeneratorSettings,
)
from airunner_services.database.models.memory_settings import (
    MemorySettings,
)
from airunner_services.database.models.metadata_settings import (
    MetadataSettings,
)
from airunner_services.database.models.openvoice_settings import (
    OpenVoiceSettings,
)
from airunner_services.database.models.path_settings import PathSettings
from airunner_services.database.models.sound_settings import SoundSettings
from airunner_services.database.models.stt_settings import STTSettings
from airunner_services.database.models.voice_settings import VoiceSettings
from airunner_services.database.models.whisper_settings import (
    WhisperSettings,
)
from airunner_services.llm.get_chatbot import get_chatbot
from airunner_services.utils.application.api_reference import (
    peek_registered_api,
)
from airunner_services.utils.application.get_logger import get_logger


SettingsModel = TypeVar("SettingsModel")

_ESPEAK_MODEL_TYPE = "eSpeak"
_OPENVOICE_MODEL_TYPE = "OpenVoice"


class RuntimeContextMixin:
    """Provide service-safe API and settings accessors."""

    def __init__(
        self,
        *args: object,
        api: Optional[object] = None,
        **kwargs: object,
    ) -> None:
        self._runtime_settings_cache: dict[type[Any], Any] = {}
        super().__init__(*args, **kwargs)
        if not hasattr(self, "logger"):
            self.logger = get_logger(self.__class__.__module__)
        if api is not None or getattr(self, "api", None) is None:
            self.api = api or self._resolve_api_reference()

    def _resolve_api_reference(self) -> Optional[object]:
        """Return the registered service API reference when available."""
        return peek_registered_api()

    def refresh_api_reference(self) -> Optional[object]:
        """Refresh one stale cached API reference when possible."""
        live_api = self._resolve_api_reference()
        if live_api is not None:
            self.api = live_api
        return getattr(self, "api", None)

    def _load_settings(
        self,
        model_cls: type[SettingsModel],
        *,
        eager_load: Optional[list[str]] = None,
    ) -> SettingsModel:
        """Return one cached or lazily loaded settings row."""
        cached = self._runtime_settings_cache.get(model_cls)
        if cached is not None:
            return cached
        settings = self._fetch_settings(model_cls, eager_load=eager_load)
        self._runtime_settings_cache[model_cls] = settings
        return settings

    def _fetch_settings(
        self,
        model_cls: type[SettingsModel],
        *,
        eager_load: Optional[list[str]] = None,
    ) -> SettingsModel:
        """Load one persisted settings row or a default object."""
        query_kwargs = {"eager_load": eager_load} if eager_load else {}
        try:
            settings = model_cls.objects.first(**query_kwargs)
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

    def _invalidate_setting_cache(self, model_cls: type[Any]) -> None:
        """Drop one cached settings row."""
        self._runtime_settings_cache.pop(model_cls, None)

    def _update_settings_model(
        self,
        model_cls: type[Any],
        **fields: object,
    ) -> Any:
        """Persist updates for one shared settings model."""
        settings = self._load_settings(model_cls)
        for key, value in fields.items():
            setattr(settings, key, value)
        save = getattr(settings, "save", None)
        if callable(save):
            save()
        self._runtime_settings_cache[model_cls] = settings
        for key, value in fields.items():
            self._notify_setting_updated(
                model_cls.__tablename__,
                key,
                value,
            )
        return settings

    def update_generator_settings(self, **fields: object) -> Any:
        """Persist art generator setting updates."""
        return self._update_settings_model(GeneratorSettings, **fields)

    def update_llm_generator_settings(self, **fields: object) -> Any:
        """Persist LLM generator setting updates."""
        return self._update_settings_model(LLMGeneratorSettings, **fields)

    def _notify_setting_updated(
        self,
        setting_name: Optional[str] = None,
        column_name: Optional[str] = None,
        val: Any = None,
    ) -> None:
        """Notify listeners that one persisted setting changed."""
        data = {
            "setting_name": setting_name,
            "column_name": column_name,
            "val": val,
        }
        api_ref = self.refresh_api_reference()
        notify = getattr(api_ref, "application_settings_changed", None)
        if callable(notify):
            notify(setting_name=setting_name, column_name=column_name, val=val)
            return
        emit = getattr(api_ref, "emit_signal", None)
        if callable(emit):
            emit(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, data)
            return
        emit = getattr(self, "emit_signal", None)
        if callable(emit):
            emit(SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL, data)

    @property
    def application_settings(self) -> Any:
        """Return persisted application settings or one default object."""
        return self._load_settings(ApplicationSettings)

    @property
    def language_settings(self) -> Any:
        """Return persisted language settings or one default object."""
        return self._load_settings(LanguageSettings)

    @property
    def sound_settings(self) -> Any:
        """Return persisted sound settings or one default object."""
        return self._load_settings(SoundSettings)

    @property
    def whisper_settings(self) -> Any:
        """Return persisted Whisper settings or one default object."""
        return self._load_settings(WhisperSettings)

    @property
    def stt_settings(self) -> Any:
        """Return persisted STT settings or one default object."""
        return self._load_settings(STTSettings)

    @property
    def llm_generator_settings(self) -> Any:
        """Return persisted LLM generator settings."""
        settings = self._load_settings(LLMGeneratorSettings)
        if getattr(settings, "enable_tools", None) is None:
            settings.enable_tools = True
        if getattr(settings, "n_ctx", None) in (None, 0):
            settings.n_ctx = 32768
        return settings

    @property
    def generator_settings(self) -> Any:
        """Return persisted art generator settings."""
        return self._load_settings(
            GeneratorSettings,
            eager_load=["aimodel"],
        )

    @property
    def memory_settings(self) -> Any:
        """Return persisted memory settings or one default object."""
        return self._load_settings(MemorySettings)

    @property
    def metadata_settings(self) -> Any:
        """Return persisted metadata settings or one default object."""
        return self._load_settings(MetadataSettings)

    @property
    def controlnet_settings(self) -> Any:
        """Return one shared ControlNet settings row."""
        return self._load_settings(ControlnetSettings)

    @property
    def path_settings(self) -> Any:
        """Return persisted path settings or one default object."""
        return self._load_settings(PathSettings)

    @property
    def chatbot(self) -> Any:
        """Return the current chatbot selection."""
        return get_chatbot()

    def _get_active_voice_settings(
        self,
        model_cls: type[Any],
        expected_model_type: str,
    ) -> Any:
        """Return the active voice-model settings row when available."""
        voice_settings = None
        settings_id = None
        if getattr(self.chatbot, "voice_id", None) is not None:
            voice_settings = self.chatbot_voice_settings
        if voice_settings and voice_settings.model_type == expected_model_type:
            settings_id = voice_settings.settings_id
        if settings_id is not None:
            settings = model_cls.objects.get(pk=settings_id)
            if settings is not None:
                self._runtime_settings_cache[model_cls] = settings
                return settings
        return self._load_settings(model_cls)

    @property
    def espeak_settings(self) -> Any:
        """Return eSpeak settings for the active voice when possible."""
        return self._get_active_voice_settings(
            EspeakSettings,
            _ESPEAK_MODEL_TYPE,
        )

    @property
    def openvoice_settings(self) -> Any:
        """Return OpenVoice settings for the active voice when possible."""
        return self._get_active_voice_settings(
            OpenVoiceSettings,
            _OPENVOICE_MODEL_TYPE,
        )

    @property
    def chatbot_voice_settings(self) -> Any:
        """Return voice settings for the current chatbot."""
        chatbot = self.chatbot
        if getattr(chatbot, "voice_id", None) is None:
            voice_settings = VoiceSettings.objects.first()
            if voice_settings is None:
                settings = self.espeak_settings
                voice_settings = VoiceSettings.objects.create(
                    name="Default Voice",
                    model_type=_ESPEAK_MODEL_TYPE,
                    settings_id=settings.id,
                )
            Chatbot.objects.update(chatbot.id, voice_id=voice_settings.id)
            chatbot.voice_id = voice_settings.id
        voice_settings = VoiceSettings.objects.get(pk=chatbot.voice_id)
        if voice_settings is None:
            raise ValueError("Chatbot voice settings not found.")
        return voice_settings


__all__ = ["RuntimeContextMixin"]