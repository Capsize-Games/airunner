"""Memory tracking mixin for ModelResourceManager."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from airunner.components.model_management.types import (
        MemoryAllocationBreakdown,
    )


class MemoryTrackingMixin:
    """Mixin for tracking non-model memory allocations.

    This mixin handles:
    - Canvas history memory tracking (VRAM + RAM)
    - External application VRAM tracking
    - Memory allocation breakdowns for reporting
    - Available VRAM calculations with all allocations

    Attributes managed:
        _canvas_history_vram_gb: VRAM used by canvas undo/redo
        _canvas_history_ram_gb: RAM used by canvas undo/redo
        _external_apps_vram_gb: VRAM used by other apps
        hardware_profiler: HardwareProfiler instance (from parent)
        memory_allocator: MemoryAllocator instance (from parent)
        logger: Logger instance (from parent)
    """

    _canvas_history_vram_gb: float
    _canvas_history_ram_gb: float
    _external_apps_vram_gb: float

    def update_canvas_history_allocation(
        self, vram_gb: float = 0.0, ram_gb: float = 0.0
    ) -> None:
        """Update canvas history memory allocation.

        Args:
            vram_gb: VRAM used by canvas history in GB
            ram_gb: RAM used by canvas history in GB
        """
        self._canvas_history_vram_gb = vram_gb
        self._canvas_history_ram_gb = ram_gb
        self.logger.debug(
            f"Canvas history allocation updated: "
            f"VRAM={vram_gb:.2f}GB, RAM={ram_gb:.2f}GB"
        )

    def update_external_apps_allocation(self, vram_gb: float = 0.0) -> None:
        """Update external application VRAM usage.

        Args:
            vram_gb: VRAM used by external applications in GB
        """
        self._external_apps_vram_gb = vram_gb
        self.logger.debug(f"External apps VRAM usage: {vram_gb:.2f}GB")

    def get_memory_allocation_breakdown(self) -> "MemoryAllocationBreakdown":
        """Get detailed breakdown of memory allocation.

        Returns:
            MemoryAllocationBreakdown with all allocation categories
        """
        from airunner.components.model_management.types import (
            MemoryAllocationBreakdown,
        )

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
        """Get available VRAM accounting for all allocations.

        Returns:
            Available VRAM in GB after all allocations
        """
        hardware = self.hardware_profiler.get_profile()
        used_by_models = self.memory_allocator.get_total_allocated_vram()

        # Account for canvas history and external apps
        total_used = (
            used_by_models
            + self._canvas_history_vram_gb
            + self._external_apps_vram_gb
            + self.memory_allocator._reserved_vram_gb
        )

        return max(0.0, hardware.available_vram_gb - total_used)
