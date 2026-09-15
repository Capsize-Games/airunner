"""Configured model identifier resolution for MainWindow."""

from __future__ import annotations

import os

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner.enums import ModelType


class ConfiguredModelResolver(MainWindowBase):
    """Resolve the configured model identifier for each runtime type."""

    def _configured_resource_model_id(self, model_type: ModelType) -> str:
        """Return the configured model identifier for one runtime."""
        if model_type is ModelType.LLM:
            return self._configured_llm_model_id()
        if model_type is ModelType.TTS:
            return self._configured_tts_resource_model_id()
        if model_type is ModelType.STT:
            return self._configured_stt_resource_model_id()
        if model_type is ModelType.SAFETY_CHECKER:
            return "Safety Checker"
        return ""

    def _configured_llm_model_id(self) -> str:
        """Return the configured LLM model identifier."""
        settings = getattr(self, "llm_generator_settings", None)
        for key in ("model_path", "model_id", "model_version"):
            value = str(getattr(settings, key, "") or "").strip()
            if value:
                return value
        return "LLM"

    def _configured_art_resource_model_id(self) -> str:
        """Return the label used for one art runtime row."""
        settings = getattr(self, "generator_settings", None)
        aimodel = getattr(settings, "aimodel", None)
        for value in (
            getattr(aimodel, "path", ""),
            getattr(settings, "custom_path", ""),
            getattr(aimodel, "name", ""),
            getattr(settings, "model_name", ""),
        ):
            resolved = str(value or "").strip()
            if resolved:
                return resolved
        return "SD"

    @staticmethod
    def _display_tts_model_name(value: str) -> str:
        """Return one user-facing TTS model name."""
        normalized = str(value or "").strip().lower()
        if normalized in {"openvoice", "tts_openvoice"}:
            return "OpenVoice"
        if normalized in {"espeak", "espeak-ng", "e-speak"}:
            return "eSpeak"
        if normalized == "tts":
            return "TTS"
        return str(value or "").strip()

    def _configured_tts_resource_model_id(self) -> str:
        """Return the label used for one TTS runtime row."""
        voice_settings = getattr(self, "chatbot_voice_settings", None)
        model_type = str(getattr(voice_settings, "model_type", "") or "")
        if model_type.strip():
            return self._display_tts_model_name(model_type)
        settings = getattr(self, "path_settings", None)
        value = str(getattr(settings, "tts_model_path", "") or "")
        return value.strip() or "TTS"

    def _configured_stt_resource_model_id(self) -> str:
        """Return the label used for one STT runtime row."""
        from airunner_common.settings import AIRUNNER_DEFAULT_STT_HF_PATH

        settings = getattr(self, "path_settings", None)
        base_path = str(getattr(settings, "stt_model_path", "") or "")
        if base_path.strip():
            return os.path.join(base_path.strip(), AIRUNNER_DEFAULT_STT_HF_PATH)
        return AIRUNNER_DEFAULT_STT_HF_PATH
