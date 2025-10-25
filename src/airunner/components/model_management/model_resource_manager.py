import logging
from typing import Optional

from airunner.components.model_management.hardware_profiler import (
    HardwareProfiler,
    HardwareProfile,
)
from airunner.components.model_management.quantization_strategy import (
    QuantizationStrategy,
    QuantizationLevel,
    QuantizationConfig,
)
from airunner.components.model_management.model_registry import (
    ModelRegistry,
    ModelMetadata,
    ModelProvider,
    ModelType,
)
from airunner.components.model_management.memory_allocator import (
    MemoryAllocator,
    MemoryAllocation,
)


class ModelResourceManager:
    """Central coordinator for all model resource operations."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self.logger = logging.getLogger(__name__)
        self.hardware_profiler = HardwareProfiler()
        self.quantization_strategy = QuantizationStrategy()
        self.registry = ModelRegistry()

        hardware = self.hardware_profiler.get_profile()
        self.memory_allocator = MemoryAllocator(hardware)

        self._initialized = True
        self._log_hardware_profile(hardware)

    def _log_hardware_profile(self, hardware: HardwareProfile) -> None:
        """Log hardware profile information."""
        self.logger.info(f"Hardware Profile:")
        self.logger.info(
            f"  VRAM: {hardware.available_vram_gb:.1f}GB / {hardware.total_vram_gb:.1f}GB"
        )
        self.logger.info(
            f"  RAM: {hardware.available_ram_gb:.1f}GB / {hardware.total_ram_gb:.1f}GB"
        )
        self.logger.info(f"  GPU: {hardware.device_name or 'None'}")
        self.logger.info(f"  CUDA: {hardware.cuda_available}")

    def select_best_model(
        self,
        provider: ModelProvider,
        model_type: ModelType,
    ) -> Optional[ModelMetadata]:
        """Select best model for current hardware."""
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

    def prepare_model_loading(
        self,
        model_id: str,
        model_type: str = "llm",
        preferred_quantization: Optional[QuantizationLevel] = None,
    ) -> dict:
        """Prepare resources for model loading."""
        metadata = self.registry.get_model(model_id)
        if not metadata:
            self.logger.warning(
                f"Model {model_id} not in registry - allowing load without validation"
            )
            return {"can_load": True, "reason": "Model not in registry"}

        hardware = self.hardware_profiler.get_profile()
        quantization = self.quantization_strategy.select_quantization(
            metadata.size_gb, hardware, preferred_quantization
        )

        allocation = self.memory_allocator.allocate(model_id, quantization)
        if not allocation:
            return {
                "can_load": False,
                "reason": "Insufficient memory",
                "metadata": metadata,
                "quantization": quantization,
            }

        self.logger.info(
            f"Prepared {metadata.name}: {quantization.description}"
        )
        return {
            "can_load": True,
            "metadata": metadata,
            "quantization": quantization,
            "allocation": allocation,
        }

    def cleanup_model(self, model_id: str, model_type: str = "llm") -> None:
        """Cleanup resources after model unloading."""
        self.memory_allocator.deallocate(model_id)

    def check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure."""
        return self.memory_allocator.is_under_memory_pressure()
