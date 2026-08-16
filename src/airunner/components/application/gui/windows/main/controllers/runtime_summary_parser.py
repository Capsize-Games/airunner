"""Daemon runtime summary parsing helpers for MainWindow."""

from __future__ import annotations

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner.enums import ModelStatus, ModelType


class RuntimeSummaryParser(MainWindowBase):
    """Parse daemon runtime summaries into GUI model statuses/names."""

    @staticmethod
    def _model_status_from_runtime_summary(summary: dict) -> ModelStatus:
        """Translate one daemon runtime summary into GUI model status."""
        runtime_status = str(summary.get("status", "")).strip().lower()
        if runtime_status == "starting":
            return ModelStatus.LOADING
        if runtime_status == "failed":
            return ModelStatus.FAILED
        if runtime_status == "ready":
            return ModelStatus.LOADED
        if bool(summary.get("loaded")):
            return ModelStatus.LOADED
        return ModelStatus.UNLOADED

    @staticmethod
    def _preferred_runtime_mode_for_model(model_type: ModelType):
        """Return the preferred daemon route for one GUI model type."""
        if model_type in {ModelType.SD, ModelType.TTS}:
            return "sidecar"
        return None

    @classmethod
    def _preferred_runtime_summaries(cls, status: dict) -> dict:
        """Return one preferred daemon summary per GUI model type."""
        runtimes = status.get("runtimes")
        if not isinstance(runtimes, list):
            return {}
        runtime_map = {
            "llm": ModelType.LLM,
            "tts": ModelType.TTS,
            "stt": ModelType.STT,
            "art": ModelType.SD,
        }
        selected: dict = {}
        for runtime in runtimes:
            model_type = runtime_map.get(str(runtime.get("runtime", "")).lower())
            if model_type is None:
                continue
            cls._select_preferred_runtime(selected, model_type, runtime)
        return selected

    @classmethod
    def _select_preferred_runtime(cls, selected, model_type, runtime) -> None:
        """Store the preferred runtime summary for one model type."""
        existing = selected.get(model_type)
        if existing is None:
            selected[model_type] = runtime
            return
        preferred_mode = cls._preferred_runtime_mode_for_model(model_type)
        if preferred_mode is None:
            return
        runtime_mode = str(runtime.get("mode", "")).strip().lower()
        existing_mode = str(existing.get("mode", "")).strip().lower()
        if runtime_mode == preferred_mode and existing_mode != preferred_mode:
            selected[model_type] = runtime

    @classmethod
    def _runtime_statuses_from_daemon_status(cls, status: dict) -> dict:
        """Return GUI model statuses derived from daemon runtime summaries."""
        return {
            model_type: cls._model_status_from_runtime_summary(runtime)
            for model_type, runtime in cls._preferred_runtime_summaries(status).items()
        }

    @staticmethod
    def _loaded_model_names_from_runtime_status(status: dict) -> set[str]:
        """Return loaded model names using runtime summaries when present."""
        runtimes = status.get("runtimes")
        if isinstance(runtimes, list):
            return RuntimeSummaryParser._loaded_names_from_runtimes(runtimes)
        lifecycle = status.get("lifecycle") or {}
        return set(lifecycle.get("loaded_models") or [])

    @staticmethod
    def _loaded_names_from_runtimes(runtimes) -> set[str]:
        """Collect loaded runtime names from a runtime summary list."""
        loaded_models = set()
        for runtime in runtimes:
            if not runtime.get("loaded"):
                continue
            runtime_name = str(runtime.get("runtime", "")).upper()
            if runtime_name == "ART":
                runtime_name = "SD"
            loaded_models.add(runtime_name)
        return loaded_models
