"""Memory allocation helpers for model resource management."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from airunner_services.model_management.hardware_profiler import (
    HardwareProfile,
)
from airunner_services.model_management.quantization_strategy import (
    QuantizationConfig,
)


@dataclass
class MemoryAllocation:
    """Memory allocation for one loaded model."""

    model_id: str
    vram_allocated_gb: float
    ram_allocated_gb: float
    device: str


class MemoryAllocator:
    """Manage VRAM and RAM allocation across loaded models."""

    def __init__(self, hardware: HardwareProfile) -> None:
        self.logger = logging.getLogger(__name__)
        self.hardware = hardware
        self._allocations: dict[str, MemoryAllocation] = {}
        self._reserved_vram_gb = 1.5
        self._reserved_ram_gb = 2.0

    def can_allocate(
        self,
        model_id: str,
        quantization: QuantizationConfig,
    ) -> bool:
        """Return whether the requested model allocation fits memory."""
        del model_id
        required_vram = quantization.estimated_memory_gb
        required_ram = max(4.0, quantization.estimated_memory_gb * 0.2)
        return (
            self._get_available_vram() >= required_vram
            and self._get_available_ram() >= required_ram
        )

    def allocate(
        self,
        model_id: str,
        quantization: QuantizationConfig,
        device: str = "cuda:0",
    ) -> MemoryAllocation | None:
        """Allocate memory for one model when capacity allows."""
        if not self.can_allocate(model_id, quantization):
            self.logger.warning("Cannot allocate memory for %s", model_id)
            return None
        allocation = MemoryAllocation(
            model_id=model_id,
            vram_allocated_gb=quantization.estimated_memory_gb,
            ram_allocated_gb=max(4.0, quantization.estimated_memory_gb * 0.2),
            device=device,
        )
        self._allocations[model_id] = allocation
        self.logger.info(
            "Allocated %.1fGB VRAM for %s",
            allocation.vram_allocated_gb,
            model_id,
        )
        return allocation

    def deallocate(self, model_id: str) -> None:
        """Release memory previously allocated for one model."""
        if model_id in self._allocations:
            del self._allocations[model_id]
            self.logger.info("Deallocated memory for %s", model_id)

    def _get_available_vram(self) -> float:
        used = sum(
            item.vram_allocated_gb for item in self._allocations.values()
        )
        return self.hardware.available_vram_gb - used - self._reserved_vram_gb

    def _get_available_ram(self) -> float:
        used = sum(
            item.ram_allocated_gb for item in self._allocations.values()
        )
        return self.hardware.available_ram_gb - used - self._reserved_ram_gb

    def get_total_allocated_vram(self) -> float:
        """Return the total allocated VRAM across all models."""
        return sum(
            item.vram_allocated_gb for item in self._allocations.values()
        )

    def get_total_allocated_ram(self) -> float:
        """Return the total allocated RAM across all models."""
        return sum(
            item.ram_allocated_gb for item in self._allocations.values()
        )

    def is_under_memory_pressure(self) -> bool:
        """Return whether the allocator is below safe headroom."""
        return (
            self._get_available_vram() < 2.0 or self._get_available_ram() < 4.0
        )
