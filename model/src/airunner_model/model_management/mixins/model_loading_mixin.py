"""Pure model-loading helpers for resource managers."""

from __future__ import annotations

from typing import Any
from typing import Optional

from airunner_model.model_management.types import ModelState

_PRIORITY_MAP = {
    "text_to_image": 3,
    "llm": 2,
    "tts": 1,
    "stt": 1,
}


class ModelLoadingMixin:
    """Mixin for load preparation and unload planning."""

    def prepare_model_loading(
        self,
        model_id: str,
        model_type: str = "llm",
        preferred_quantization: Optional[Any] = None,
        auto_swap: bool = True,
    ) -> dict[str, Any]:
        """Prepare memory and swap state for one model load."""
        self.set_model_state(model_id, ModelState.LOADING, model_type)
        metadata = self.registry.get_model(model_id)
        if metadata is None:
            return self._prepare_unregistered_model(
                model_id,
                model_type,
                auto_swap,
            )
        quantization = self._select_quantization(
            metadata.size_gb,
            preferred_quantization,
        )
        allocation, swapped_models = self._allocate_for_model(
            model_id,
            model_type,
            quantization,
            auto_swap,
        )
        if allocation is None:
            return self._allocation_failure_response(
                model_id,
                metadata,
                quantization,
            )
        self.logger.info(
            "Prepared %s: %s",
            metadata.name,
            quantization.description,
        )
        return {
            "can_load": True,
            "metadata": metadata,
            "quantization": quantization,
            "allocation": allocation,
            "swapped_models": swapped_models,
        }

    def _prepare_unregistered_model(
        self,
        model_id: str,
        model_type: str,
        auto_swap: bool,
    ) -> dict[str, Any]:
        """Handle load planning for one model that is not in the registry."""
        self.logger.warning(
            "Model %s not in registry - checking for conflicts anyway",
            model_id,
        )
        if not auto_swap:
            return self._unregistered_model_response(
                "Model not in registry - no validation performed",
            )
        active_models = [
            model
            for model in self.get_active_models()
            if model.model_id != model_id
        ]
        if not active_models:
            return self._unregistered_model_response(
                "Model not in registry - no validation performed",
            )
        self.logger.info(
            "Found %s active models while loading unregistered model",
            len(active_models),
        )
        swap_result = self.request_model_swap(model_id, model_type)
        if swap_result["success"] and swap_result["unloaded_models"]:
            self.logger.info(
                "Auto-swapped %s models for unregistered model",
                len(swap_result["unloaded_models"]),
            )
            return {
                "can_load": True,
                "reason": (
                    "Model not in registry but made room via auto-swap"
                ),
                "swapped_models": swap_result["unloaded_models"],
            }
        self.logger.warning(
            "Auto-swap did not unload any models. Proceeding anyway but OOM likely."
        )
        return self._unregistered_model_response(
            "Model not in registry - no validation performed",
        )

    @staticmethod
    def _unregistered_model_response(reason: str) -> dict[str, Any]:
        """Return the standard response for an unregistered model."""
        return {
            "can_load": True,
            "reason": reason,
            "swapped_models": [],
        }

    def _select_quantization(
        self,
        model_size_gb: float,
        preferred_quantization: Optional[Any],
    ) -> Any:
        """Select quantization for one model against current hardware."""
        hardware = self.hardware_profiler.get_profile()
        return self.quantization_strategy.select_quantization(
            model_size_gb,
            hardware,
            preferred_quantization,
        )

    def _allocate_for_model(
        self,
        model_id: str,
        model_type: str,
        quantization: Any,
        auto_swap: bool,
    ) -> tuple[Any | None, list[str]]:
        """Allocate memory directly or after a best-effort swap."""
        allocation = self.memory_allocator.allocate(model_id, quantization)
        if allocation is not None or not auto_swap:
            return allocation, []
        self.logger.info(
            "Insufficient memory for %s, attempting auto-swap",
            model_id,
        )
        swap_result = self.request_model_swap(model_id, model_type)
        if not swap_result["success"]:
            return None, []
        allocation = self.memory_allocator.allocate(model_id, quantization)
        if allocation is None:
            return None, []
        self.logger.info(
            "Prepared %s after auto-swap: %s",
            model_id,
            quantization.description,
        )
        return allocation, list(swap_result["unloaded_models"])

    def _allocation_failure_response(
        self,
        model_id: str,
        metadata: Any,
        quantization: Any,
    ) -> dict[str, Any]:
        """Return the standard failure response for one load attempt."""
        self.set_model_state(model_id, ModelState.UNLOADED)
        return {
            "can_load": False,
            "reason": "Insufficient memory even after attempting model swap",
            "metadata": metadata,
            "quantization": quantization,
            "swapped_models": [],
        }

    def request_model_swap(
        self,
        target_model_id: str,
        target_model_type: str,
    ) -> dict[str, Any]:
        """Unload lower-priority models to make room for one target model."""
        models_to_unload = self._determine_models_to_unload(
            target_model_id,
            target_model_type,
        )
        if not models_to_unload:
            return {
                "success": True,
                "unloaded_models": [],
                "reason": "No models need to be unloaded",
            }
        unloaded: list[str] = []
        for model_id in models_to_unload:
            model_type = self._model_types.get(model_id, "unknown")
            self.logger.info(
                "Auto-swapping: Unloading %s model %s",
                model_type,
                model_id,
            )
            try:
                self._unload_model_for_swap(model_id, model_type)
            except Exception as exc:
                self.logger.error(
                    "Failed to unload %s: %s",
                    model_id,
                    exc,
                    exc_info=True,
                )
                return {
                    "success": False,
                    "unloaded_models": unloaded,
                    "reason": f"Failed to unload {model_id}: {exc}",
                }
            unloaded.append(model_id)
        return {
            "success": True,
            "unloaded_models": unloaded,
            "reason": f"Successfully unloaded {len(unloaded)} models",
        }

    def _determine_models_to_unload(
        self,
        target_model_id: str,
        target_model_type: str,
    ) -> list[str]:
        """Return lower-priority loaded models that can be unloaded."""
        del target_model_id
        target_priority = _PRIORITY_MAP.get(target_model_type, 2)
        self.logger.debug(
            "Determining models to unload for %s (priority %s)",
            target_model_type,
            target_priority,
        )
        candidates = self._unload_candidates(target_priority)
        models_to_unload = [model_id for model_id, _, _, _ in candidates]
        if models_to_unload:
            self.logger.info(
                "Selected %s models for unloading: %s",
                len(models_to_unload),
                models_to_unload,
            )
        else:
            self.logger.warning(
                "No models selected for unloading despite %s tracked models",
                len(self._model_states),
            )
        return models_to_unload

    def _unload_candidates(
        self,
        target_priority: int,
    ) -> list[tuple[str, str, int, float]]:
        """Return unloadable models sorted by priority and VRAM usage."""
        candidates: list[tuple[str, str, int, float]] = []
        self.logger.debug(
            "Current model states: %s",
            list(self._model_states.items()),
        )
        for model_id, state in self._model_states.items():
            candidate = self._candidate_for_model(
                model_id,
                state,
                target_priority,
            )
            if candidate is not None:
                candidates.append(candidate)
        candidates.sort(key=lambda item: (item[2], -item[3]))
        return candidates

    def _candidate_for_model(
        self,
        model_id: str,
        state: ModelState,
        target_priority: int,
    ) -> tuple[str, str, int, float] | None:
        """Return one unload candidate when the model qualifies."""
        if state not in (ModelState.LOADED, ModelState.UNLOADED):
            self.logger.debug(
                "Skipping %s - state %s not eligible for unload",
                model_id,
                state,
            )
            return None
        if state is ModelState.UNLOADED:
            self.logger.debug("Skipping %s - already unloaded", model_id)
            return None
        model_type = self._model_types.get(model_id, "unknown")
        model_priority = _PRIORITY_MAP.get(model_type, 2)
        self.logger.debug(
            "Checking %s: type=%s, priority=%s, target_priority=%s",
            model_id,
            model_type,
            model_priority,
            target_priority,
        )
        if model_priority > target_priority:
            self.logger.debug(
                "Skipping %s - priority %s > target %s",
                model_id,
                model_priority,
                target_priority,
            )
            return None
        allocation = self.memory_allocator._allocations.get(model_id)
        if allocation is None:
            self.logger.debug(
                "Skipping %s - no allocation record found",
                model_id,
            )
            return None
        self.logger.debug(
            "Added %s as unload candidate (VRAM: %.1fGB)",
            model_id,
            allocation.vram_allocated_gb,
        )
        return (
            model_id,
            model_type,
            model_priority,
            allocation.vram_allocated_gb,
        )

    def _unload_model_for_swap(self, model_id: str, model_type: str) -> None:
        """Unload one active model through the host application."""
        del model_id, model_type
        raise NotImplementedError("Model swap unloading is not configured")


__all__ = ["ModelLoadingMixin"]