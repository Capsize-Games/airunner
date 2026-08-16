"""Shared resource-manager state application for MainWindow."""

from __future__ import annotations

from airunner.components.application.gui.windows.main.controllers.base import (
    MainWindowBase,
)
from airunner.components.model_management import ModelResourceManager
from airunner.components.model_management.types import ModelState
from airunner.enums import ModelStatus


class ResourceStateApplicator(MainWindowBase):
    """Apply daemon runtime summaries to the shared resource manager."""

    @classmethod
    def _apply_runtime_resource_state(
        cls, manager, model_type: str, model_id, model_status: ModelStatus
    ) -> None:
        """Apply one daemon runtime summary to the shared resource state."""
        active_ids = cls._active_resource_model_ids(manager, model_type)
        if model_status not in (ModelStatus.LOADING, ModelStatus.LOADED):
            cls._cleanup_unloaded_models(manager, model_type, active_ids)
            return
        if not model_id:
            return
        cls._cleanup_competing_models(manager, model_type, active_ids, model_id)
        cls._apply_loaded_state(manager, model_type, model_id, model_status)

    @classmethod
    def _cleanup_unloaded_models(cls, manager, model_type, active_ids) -> None:
        """Cleanup all active models for an unloaded runtime."""
        for active_id in active_ids:
            manager.cleanup_model(active_id, model_type)

    @classmethod
    def _cleanup_competing_models(
        cls, manager, model_type, active_ids, model_id
    ) -> None:
        """Cleanup active models that differ from the desired model id."""
        for active_id in active_ids:
            if active_id != model_id:
                manager.cleanup_model(active_id, model_type)

    @staticmethod
    def _apply_loaded_state(manager, model_type, model_id, model_status) -> None:
        """Set the loaded/loading state for one model id."""
        if model_status is ModelStatus.LOADING:
            manager.set_model_state(model_id, ModelState.LOADING, model_type)
            return
        manager.model_loaded(model_id, model_type)

    @staticmethod
    def _active_resource_model_ids(manager, model_type: str) -> list[str]:
        """Return active model IDs tracked for one resource-manager type."""
        return [
            model.model_id
            for model in manager.get_active_models()
            if getattr(model, "model_type", "") == model_type
        ]
