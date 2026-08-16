"""Daemon runtime -> resource-manager mapping helpers for MainWindow."""

from __future__ import annotations

from typing import Optional

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner.components.application.gui.windows.main.controllers.configured_model_resolver import (
    ConfiguredModelResolver,
)
from airunner.components.application.gui.windows.main.controllers.resource_state_applicator import (
    ResourceStateApplicator,
)
from airunner.components.application.gui.windows.main.controllers.runtime_summary_parser import (
    RuntimeSummaryParser,
)
from airunner.components.model_management import ModelResourceManager
from airunner.enums import ModelStatus, ModelType


class RuntimeResourceMapper(
    ConfiguredModelResolver,
    ResourceStateApplicator,
    RuntimeSummaryParser,
):
    """Resolve daemon runtime state into shared resource-manager state."""

    def _sync_model_resource_manager_from_daemon(self, status: dict) -> None:
        """Mirror daemon runtime state into the shared resource manager."""
        preferred_runtimes = self._preferred_runtime_summaries(status)
        if not preferred_runtimes:
            return
        manager = ModelResourceManager()
        for runtime in preferred_runtimes.values():
            model_type = self._resource_model_type_from_runtime(runtime)
            if model_type is None:
                continue
            model_status = self._model_status_from_runtime_summary(runtime)
            model_id = self._resource_model_id_from_runtime(
                runtime, manager, model_type
            )
            self._apply_runtime_resource_state(
                manager, model_type, model_id, model_status
            )

    def _sync_model_resource_manager_from_status_signal(
        self, data: dict, model_type: ModelType, status: ModelStatus
    ) -> None:
        """Mirror a direct status signal into the shared resource widget."""
        resource_type = self._resource_model_type_from_status_signal(model_type)
        if resource_type is None:
            return
        manager = ModelResourceManager()
        model_id = self._resource_model_id_from_status_signal(
            data, manager, model_type, resource_type, status
        )
        status = self._normalize_signal_status(status)
        if self._is_stale_loading_state(manager, model_id, status):
            return
        self._apply_runtime_resource_state(
            manager, resource_type, model_id, status
        )

    @staticmethod
    def _normalize_signal_status(status: ModelStatus) -> ModelStatus:
        """Normalize READY to LOADED for the shared resource widget."""
        if status is ModelStatus.READY:
            return ModelStatus.LOADED
        return status

    @staticmethod
    def _is_stale_loading_state(manager, model_id, status: ModelStatus) -> bool:
        """Return True for a stale loading update on a loaded/busy model."""
        from airunner.components.model_management.types import ModelState

        current_state = manager.get_model_state(model_id) if model_id else None
        return (
            status is ModelStatus.LOADING
            and current_state in (ModelState.LOADED, ModelState.BUSY)
        )

    @staticmethod
    def _resource_model_type_from_runtime(runtime: dict) -> Optional[str]:
        """Return the resource-manager type for one daemon runtime."""
        runtime_name = str(runtime.get("runtime", "")).strip().lower()
        return {
            "art": "text_to_image",
            "llm": "llm",
            "stt": "stt",
            "tts": "tts",
        }.get(runtime_name)

    @staticmethod
    def _resource_model_type_from_status_signal(model_type: ModelType):
        """Return the resource-manager type for one direct status signal."""
        return {
            ModelType.LLM: "llm",
            ModelType.TTS: "tts",
            ModelType.STT: "stt",
            ModelType.SAFETY_CHECKER: "safety_checker",
        }.get(model_type)

    def _resource_model_id_from_runtime(
        self, runtime: dict, manager, model_type: str
    ) -> Optional[str]:
        """Resolve one daemon runtime summary to a stable model ID."""
        runtime_name = str(runtime.get("runtime", "") or "").strip().lower()
        resolved = self._runtime_metadata_model_id(
            runtime_name, runtime.get("metadata") or {}
        )
        if resolved:
            return resolved
        active_ids = self._active_resource_model_ids(manager, model_type)
        if active_ids:
            return active_ids[0]
        return self._generic_runtime_fallback(runtime_name)

    @staticmethod
    def _generic_runtime_fallback(runtime_name: str) -> Optional[str]:
        """Return a stable generic label for one runtime name."""
        if runtime_name == "art":
            return "SD"
        if runtime_name in {"llm", "stt", "tts"}:
            return runtime_name.upper()
        return None

    @classmethod
    def _runtime_metadata_model_id(cls, runtime_name: str, metadata: dict):
        """Return one non-generic model identifier from runtime metadata."""
        for key in ("model_path", "model_id", "model_version"):
            value = str(metadata.get(key, "") or "").strip()
            if value:
                return value
        model_type = str(metadata.get("model_type", "") or "").strip()
        if model_type and not cls._is_generic_runtime_model_id(model_type, runtime_name):
            return model_type
        return None

    @staticmethod
    def _is_generic_runtime_model_id(value: str, runtime_name: str) -> bool:
        """Return whether one runtime model identifier is too generic."""
        normalized = str(value or "").strip().lower()
        generic_ids = {
            runtime_name,
            f"{runtime_name} model",
            "art",
            "sd",
            "sd model",
            "llm",
            "llm model",
            "stt",
            "stt model",
            "text_to_image",
            "tts",
            "tts model",
        }
        return normalized in generic_ids

    def _resource_model_id_from_status_signal(
        self,
        data: dict,
        manager,
        model_type: ModelType,
        resource_type: str,
        status: ModelStatus,
    ) -> Optional[str]:
        """Resolve one stable model ID from a direct status signal."""
        for key in ("model_path", "path", "model_id"):
            value = str(data.get(key, "") or "").strip()
            if value:
                return value
        active_ids = self._active_resource_model_ids(manager, resource_type)
        if status in (ModelStatus.UNLOADED, ModelStatus.FAILED) and active_ids:
            return active_ids[0]
        return self._configured_or_active_id(model_type, active_ids)

    def _configured_or_active_id(self, model_type, active_ids) -> Optional[str]:
        """Return the configured model id, or the first active id."""
        configured = self._configured_resource_model_id(model_type)
        if configured:
            return configured
        if active_ids:
            return active_ids[0]
        return None
