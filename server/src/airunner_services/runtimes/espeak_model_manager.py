"""Service-owned eSpeak runtime manager."""

from __future__ import annotations

from abc import ABCMeta
from typing import Optional

import pyttsx3

from airunner_services.contract_enums import AvailableLanguage
from airunner_services.contract_enums import Gender
from airunner_services.contract_enums import ModelStatus
from airunner_services.contract_enums import ModelType
from airunner_services.database.models.espeak_settings import EspeakSettings
from airunner_services.requests.tts_request import TTSRequest
from airunner_services.runtimes.tts_model_manager import TTSModelManager


class EspeakModelManager(TTSModelManager, metaclass=ABCMeta):
    """Manage the local eSpeak TTS runtime."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tts_request: Optional[TTSRequest] = None
        self._engine = None

    @property
    def espeak_settings(self) -> EspeakSettings:
        """Return persisted eSpeak settings or one default row."""
        return self._load_settings(EspeakSettings)

    def _setting_value(self, name: str, fallback):
        """Return one persisted eSpeak setting with a default fallback."""
        value = getattr(self.espeak_settings, name, None)
        if value in (None, ""):
            return fallback
        return value

    @property
    def gender(self) -> str:
        """Return the active request gender or the stored default."""
        gender = super().gender
        if gender:
            return gender
        return str(self._setting_value("gender", Gender.MALE.value))

    @property
    def language(self) -> AvailableLanguage:
        """Return the active request language with a safe default."""
        if self.tts_request:
            lang = getattr(self.tts_request, "language", None)
            if isinstance(lang, AvailableLanguage):
                return lang
            if isinstance(lang, str):
                normalized = lang.upper().replace("-", "_")
                alias = {"EN_US": "EN", "ENGLISH": "EN"}.get(
                    normalized,
                    normalized,
                )
                if alias in AvailableLanguage.__members__:
                    return AvailableLanguage[alias]
        return AvailableLanguage.EN

    @property
    def voice(self) -> str:
        """Return the active request voice or the stored default."""
        if self.tts_request:
            voice = getattr(self.tts_request, "voice", None)
            if voice:
                return str(voice)
        return str(self._setting_value("voice", "english (america)"))

    @property
    def volume(self) -> int:
        """Return the active request volume or the stored default."""
        if self.tts_request:
            volume = getattr(self.tts_request, "volume", None)
            if volume is not None:
                return int(volume)
        return int(self._setting_value("volume", 100))

    @property
    def pitch(self) -> int:
        """Return the active request pitch or the stored default."""
        if self.tts_request:
            pitch = getattr(self.tts_request, "pitch", None)
            if pitch is not None:
                return int(pitch)
        return int(self._setting_value("pitch", 100))

    @property
    def rate(self) -> int:
        """Return the active request rate or the stored default."""
        if self.tts_request:
            rate = getattr(self.tts_request, "rate", None)
            if rate is not None:
                return int(rate)
        return int(self._setting_value("rate", 100))

    @property
    def status(self) -> ModelStatus:
        """Return the current eSpeak runtime state."""
        return self._model_status.get(ModelType.TTS, ModelStatus.UNLOADED)

    def generate(self, tts_request: TTSRequest):
        """Generate speech for one request when the engine is ready."""
        if not self._engine or self.status is not ModelStatus.LOADED:
            self.logger.warning(
                "TTS engine not available or not loaded. Current status: %s",
                self.status,
            )
            return None

        self.tts_request = tts_request
        message = tts_request.message.replace('"', "'")
        if not message:
            return None
        try:
            self._engine.say(message)
            self._engine.runAndWait()
        except Exception as exc:
            self.logger.error("Error during speech generation: %s", exc)
        return None

    def load(self, target_model=None):
        """Load and initialize the eSpeak engine."""
        del target_model
        if self.status in (ModelStatus.LOADING, ModelStatus.LOADED):
            self.logger.debug(
                "Espeak engine already in %s state, skipping initialization",
                self.status,
            )
            return

        self.logger.debug(
            "Initializing espeak (current status: %s)",
            self.status,
        )
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        try:
            self._engine = pyttsx3.init()
            self._initialize()
            self.logger.debug(
                "Espeak engine initialization complete, status: %s",
                self.status,
            )
        except Exception as exc:
            self.logger.error("Failed to initialize espeak: %s", exc)
            self._engine = None
            self.change_model_status(ModelType.TTS, ModelStatus.FAILED)

    def unload(self):
        """Unload the active eSpeak engine."""
        if self.status is ModelStatus.UNLOADED:
            return
        self.logger.debug("Unloading espeak")
        self.change_model_status(ModelType.TTS, ModelStatus.UNLOADED)
        self._engine = None

    def reload_speaker_embeddings(self, reference_speaker_path=None):
        """No-op hook for API compatibility with OpenVoice."""
        del reference_speaker_path

    def unblock_tts_generator_signal(self):
        """No-op compatibility hook for worker callbacks."""

    def interrupt_process_signal(self):
        """No-op compatibility hook for worker callbacks."""

    def _initialize(self):
        """Configure the loaded eSpeak engine with current settings."""
        if not self._engine:
            self.logger.error(
                "Engine not initialized before calling _initialize"
            )
            return

        try:
            self._engine.setProperty("rate", float(self.rate))
            self._engine.setProperty("volume", self.volume / 100.0)
            self._engine.setProperty("pitch", float(self.pitch))

            available_voices = self._engine.getProperty("voices")
            if not available_voices:
                self.logger.warning(
                    "No voices available in the pyttsx3 engine"
                )
                return

            selected_voice = available_voices[0]
            voice_to_match = self.voice.lower()
            gender_to_set = self.gender

            for voice in available_voices:
                voice_id = voice.id.lower()
                if voice_to_match in voice_id:
                    selected_voice = voice
                    if (
                        gender_to_set == Gender.FEMALE.value
                        and "female" in voice_id
                    ):
                        break
                    if (
                        gender_to_set == Gender.MALE.value
                        and "male" in voice_id
                    ):
                        break

            self.logger.debug("Selected voice: %s", selected_voice.id)
            self._engine.setProperty("voice", selected_voice.id)
            self.change_model_status(ModelType.TTS, ModelStatus.LOADED)
        except Exception as exc:
            self.logger.error(
                "Error initializing espeak engine properties: %s",
                exc,
            )
            self.change_model_status(ModelType.TTS, ModelStatus.FAILED)


__all__ = ["EspeakModelManager"]
