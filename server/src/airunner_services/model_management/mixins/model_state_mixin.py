"""Model state management mixin for model resource managers."""

from __future__ import annotations

from airunner_services.model_management.types import ActiveModelInfo
from airunner_services.model_management.types import ModelState


class ModelStateMixin:
    """Mixin for managing model lifecycle states."""

    def set_model_state(
        self,
        model_id: str,
        state: ModelState,
        model_type: str | None = None,
    ) -> None:
        """Update one model state entry."""
        if model_type is not None:
            self._model_types[model_id] = model_type
        self._model_states[model_id] = state

    def get_model_state(self, model_id: str) -> ModelState:
        """Return the current state for one model."""
        return self._model_states.get(model_id, ModelState.UNLOADED)

    def model_loaded(
        self,
        model_id: str,
        model_type: str | None = None,
    ) -> None:
        """Mark one model as loaded."""
        self.set_model_state(model_id, ModelState.LOADED, model_type)

    def model_busy(
        self,
        model_id: str,
        model_type: str | None = None,
    ) -> None:
        """Mark one model as busy."""
        self.set_model_state(model_id, ModelState.BUSY, model_type)

    def model_ready(
        self,
        model_id: str,
        model_type: str | None = None,
    ) -> None:
        """Mark one model as ready after processing."""
        self.set_model_state(model_id, ModelState.LOADED, model_type)

    def cleanup_model(self, model_id: str, model_type: str = "llm") -> None:
        """Cleanup resources after one model unloads."""
        self.set_model_state(model_id, ModelState.UNLOADING, model_type)
        self.memory_allocator.deallocate(model_id)
        self.set_model_state(model_id, ModelState.UNLOADED)

    def _model_name_from_id(self, model_id: str) -> str:
        """Derive a display name from the model identifier (typically a path)."""
        import os
        return os.path.basename(model_id) or model_id

    def get_active_models(self) -> list[ActiveModelInfo]:
        """Return all tracked models that are not unloaded."""
        active_models: list[ActiveModelInfo] = []
        for model_id, state in self._model_states.items():
            if state == ModelState.UNLOADED:
                continue
            allocation = self.memory_allocator._allocations.get(model_id)
            active_models.append(
                ActiveModelInfo(
                    model_id=model_id,
                    model_type=self._model_types.get(model_id, "unknown"),
                    state=state,
                    vram_allocated_gb=(
                        allocation.vram_allocated_gb if allocation else 0.0
                    ),
                    ram_allocated_gb=(
                        allocation.ram_allocated_gb if allocation else 0.0
                    ),
                    can_unload=(state == ModelState.LOADED),
                    name=self._model_name_from_id(model_id),
                )
            )
        return active_models