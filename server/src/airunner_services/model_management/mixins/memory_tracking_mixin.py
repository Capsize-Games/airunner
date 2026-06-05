"""Memory tracking mixin for model resource managers."""

from __future__ import annotations

from airunner_services.model_management.types import MemoryAllocationBreakdown


class MemoryTrackingMixin:
    """Mixin for tracking non-model memory allocations."""

    _canvas_history_vram_gb: float
    _canvas_history_ram_gb: float
    _external_apps_vram_gb: float

    def update_canvas_history_allocation(
        self,
        vram_gb: float = 0.0,
        ram_gb: float = 0.0,
    ) -> None:
        """Update canvas history memory accounting."""
        self._canvas_history_vram_gb = vram_gb
        self._canvas_history_ram_gb = ram_gb
        self.logger.debug(
            "Canvas history allocation updated: VRAM=%.2fGB, RAM=%.2fGB",
            vram_gb,
            ram_gb,
        )

    def update_external_apps_allocation(self, vram_gb: float = 0.0) -> None:
        """Update external application VRAM accounting."""
        self._external_apps_vram_gb = vram_gb
        self.logger.debug("External apps VRAM usage: %.2fGB", vram_gb)

    def get_memory_allocation_breakdown(self) -> MemoryAllocationBreakdown:
        """Return a detailed breakdown of current memory allocation."""
        hardware = self.hardware_profiler.get_profile()
        return MemoryAllocationBreakdown(
            models_vram_gb=self.memory_allocator.get_total_allocated_vram(),
            canvas_history_vram_gb=self._canvas_history_vram_gb,
            canvas_history_ram_gb=self._canvas_history_ram_gb,
            system_reserve_vram_gb=self.memory_allocator._reserved_vram_gb,
            system_reserve_ram_gb=self.memory_allocator._reserved_ram_gb,
            external_apps_vram_gb=self._external_apps_vram_gb,
            total_available_vram_gb=hardware.available_vram_gb,
            total_available_ram_gb=hardware.available_ram_gb,
        )

    def _get_available_vram_with_allocations(self) -> float:
        """Return available VRAM after all tracked allocations."""
        hardware = self.hardware_profiler.get_profile()
        used_by_models = self.memory_allocator.get_total_allocated_vram()
        total_used = (
            used_by_models
            + self._canvas_history_vram_gb
            + self._external_apps_vram_gb
            + self.memory_allocator._reserved_vram_gb
        )
        return max(0.0, hardware.available_vram_gb - total_used)
