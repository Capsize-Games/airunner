"""Model selection mixin for model resource managers."""

from __future__ import annotations

from airunner_services.model_management.model_registry import ModelMetadata
from airunner_services.model_management.model_registry import ModelProvider
from airunner_services.model_management.model_registry import ModelType


class ModelSelectionMixin:
    """Mixin for selecting the best model for current hardware."""

    def select_best_model(
        self,
        provider: ModelProvider,
        model_type: ModelType,
    ) -> ModelMetadata | None:
        """Return the largest feasible model for current hardware."""
        hardware = self.hardware_profiler.get_profile()
        models = self.registry.list_models(provider, model_type)
        suitable = [
            model
            for model in models
            if model.min_vram_gb <= hardware.available_vram_gb
            and model.min_ram_gb <= hardware.available_ram_gb
        ]
        if not suitable:
            self.logger.warning("No suitable %s models found", provider.value)
            return None
        return max(suitable, key=lambda model: model.size_gb)
