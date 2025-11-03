"""Model state management mixin for ModelResourceManager."""

from typing import List


class ModelStateMixin:
    """Mixin for managing model lifecycle states.

    This mixin handles:
    - Model state transitions (unloaded, loading, loaded, busy, unloading)
    - State queries and tracking
    - Active model inventory

    Attributes managed:
        _model_states: Dict tracking model ID to current state
        _model_types: Dict tracking model ID to model type
        logger: Logger instance (from parent class)
        memory_allocator: MemoryAllocator instance (from parent class)
    """

    def set_model_state(
        self, model_id: str, state, model_type: str = None
    ) -> None:
        """Update model state.

        Args:
            model_id: Identifier for the model
            state: New state for the model
            model_type: Optional type of model (llm, text_to_image, etc.)
        """
        self._model_states[model_id] = state

    def get_model_state(self, model_id: str):
        """Get current model state.

        Args:
            model_id: Identifier for the model

        Returns:
            Current ModelState, or UNLOADED if not tracked
        """
        from airunner.components.model_management.types import ModelState

        return self._model_states.get(model_id, ModelState.UNLOADED)

    def model_loaded(self, model_id: str) -> None:
        """Mark model as loaded successfully.

        Args:
            model_id: Unique identifier for the model
        """
        from airunner.components.model_management.types import ModelState

        self.set_model_state(model_id, ModelState.LOADED)

    def model_busy(self, model_id: str) -> None:
        """Mark model as busy (generating/processing).

        Args:
            model_id: Unique identifier for the model
        """
        from airunner.components.model_management.types import ModelState

        self.set_model_state(model_id, ModelState.BUSY)

    def model_ready(self, model_id: str) -> None:
        """Mark model as ready (finished processing).

        Args:
            model_id: Unique identifier for the model
        """
        from airunner.components.model_management.types import ModelState

        self.set_model_state(model_id, ModelState.LOADED)

    def cleanup_model(self, model_id: str, model_type: str = "llm") -> None:
        """Cleanup resources after model unloading.

        Args:
            model_id: Unique identifier for the model
            model_type: Type of model being cleaned up
        """
        from airunner.components.model_management.types import ModelState

        self.set_model_state(model_id, ModelState.UNLOADING, model_type)
        self.memory_allocator.deallocate(model_id)
        self.set_model_state(model_id, ModelState.UNLOADED)

    def get_active_models(self) -> List:
        """Get list of all active models with their states.

        Returns:
            List of ActiveModelInfo for all non-unloaded models
        """
        from airunner.components.model_management.types import (
            ModelState,
            ActiveModelInfo,
        )

        active_models = []

        for model_id, state in self._model_states.items():
            if state == ModelState.UNLOADED:
                continue

            # Try to get allocation info
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
                )
            )

        return active_models
