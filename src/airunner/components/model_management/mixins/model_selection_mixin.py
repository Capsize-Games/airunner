"""Model selection mixin for ModelResourceManager."""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from airunner.components.model_management.model_registry import (
        ModelMetadata,
        ModelProvider,
        ModelType,
    )


class ModelSelectionMixin:
    """Mixin for selecting best model for current hardware.

    This mixin handles:
    - Selecting optimal model based on available resources
    - Filtering models by hardware constraints
    - Choosing largest feasible model

    Dependencies (from parent):
        hardware_profiler: HardwareProfiler instance
        registry: ModelRegistry instance
        logger: Logger instance
    """

    def select_best_model(
        self,
        provider: "ModelProvider",
        model_type: "ModelType",
    ) -> Optional["ModelMetadata"]:
        """Select best model for current hardware.

        Args:
            provider: Model provider (e.g., huggingface, openai)
            model_type: Type of model (llm, text_to_image, etc.)

        Returns:
            ModelMetadata for best model, or None if no suitable model
        """
        hardware = self.hardware_profiler.get_profile()
        models = self.registry.list_models(provider, model_type)

        suitable = [
            m
            for m in models
            if m.min_vram_gb <= hardware.available_vram_gb
            and m.min_ram_gb <= hardware.available_ram_gb
        ]

        if not suitable:
            self.logger.warning(f"No suitable {provider.value} models found")
            return None

        return max(suitable, key=lambda m: m.size_gb)
