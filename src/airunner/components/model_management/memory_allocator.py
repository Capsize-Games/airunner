from dataclasses import dataclass
from typing import Dict, Optional

from airunner.components.model_management.hardware_profiler import (
    HardwareProfile,
)
from airunner.components.model_management.quantization_strategy import (
    QuantizationConfig,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


@dataclass
class MemoryAllocation:
    """Memory allocation for a model."""

    model_id: str
    vram_allocated_gb: float
    ram_allocated_gb: float
    device: str


class MemoryAllocator:
    """Manages VRAM and RAM allocation across loaded models."""

    def __init__(self, hardware: HardwareProfile):
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self.hardware = hardware
        self._allocations: Dict[str, MemoryAllocation] = {}
        self._reserved_vram_gb = 1.5
        self._reserved_ram_gb = 2.0

    def can_allocate(
        self,
        model_id: str,
        quantization: QuantizationConfig,
    ) -> bool:
        """Check if model can be allocated given current usage."""
        required_vram = quantization.estimated_memory_gb
        required_ram = max(4.0, quantization.estimated_memory_gb * 0.2)

        available_vram = self._get_available_vram()
        available_ram = self._get_available_ram()

        return (
            available_vram >= required_vram and available_ram >= required_ram
        )

    def allocate(
        self,
        model_id: str,
        quantization: QuantizationConfig,
        device: str = "cuda:0",
    ) -> Optional[MemoryAllocation]:
        """Allocate memory for a model."""
        if not self.can_allocate(model_id, quantization):
            self.logger.warning(f"Cannot allocate memory for {model_id}")
            return None

        allocation = MemoryAllocation(
            model_id=model_id,
            vram_allocated_gb=quantization.estimated_memory_gb,
            ram_allocated_gb=max(4.0, quantization.estimated_memory_gb * 0.2),
            device=device,
        )

        self._allocations[model_id] = allocation
        self.logger.info(
            f"Allocated {allocation.vram_allocated_gb:.1f}GB VRAM for {model_id}"
        )
        return allocation

    def deallocate(self, model_id: str) -> None:
        """Deallocate memory for a model."""
        if model_id in self._allocations:
            del self._allocations[model_id]
            self.logger.info(f"Deallocated memory for {model_id}")

    def _get_available_vram(self) -> float:
        """Get available VRAM accounting for allocations and reserve."""
        used = sum(a.vram_allocated_gb for a in self._allocations.values())
        return self.hardware.available_vram_gb - used - self._reserved_vram_gb

    def _get_available_ram(self) -> float:
        """Get available RAM accounting for allocations and reserve."""
        used = sum(a.ram_allocated_gb for a in self._allocations.values())
        return self.hardware.available_ram_gb - used - self._reserved_ram_gb

    def get_total_allocated_vram(self) -> float:
        """Get total allocated VRAM across all models."""
        return sum(a.vram_allocated_gb for a in self._allocations.values())

    def get_total_allocated_ram(self) -> float:
        """Get total allocated RAM across all models."""
        return sum(a.ram_allocated_gb for a in self._allocations.values())

    def is_under_memory_pressure(self) -> bool:
        """Check if system is under memory pressure."""
        vram_available = self._get_available_vram()
        ram_available = self._get_available_ram()

        return vram_available < 2.0 or ram_available < 4.0
