"""Canvas history memory tracking for model resource management."""

from __future__ import annotations

import logging
from typing import Any, Protocol


class CanvasSceneLike(Protocol):
    """Minimal canvas scene contract used for history-memory estimates."""

    undo_history: list[dict[str, Any]]
    redo_history: list[dict[str, Any]]


class CanvasMemoryTracker:
    """Track memory usage of canvas history."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._memory_cache: dict[int, tuple[float, float]] = {}

    def estimate_history_memory(
        self,
        scene: CanvasSceneLike,
    ) -> tuple[float, float]:
        """Estimate VRAM and RAM usage for canvas history."""
        try:
            total_vram_mb = 0.0
            total_ram_mb = 0.0
            for entry in [*scene.undo_history, *scene.redo_history]:
                vram_mb, ram_mb = self._cached_entry_memory(entry)
                total_vram_mb += vram_mb
                total_ram_mb += ram_mb
            return total_vram_mb / 1024.0, total_ram_mb / 1024.0
        except Exception as error:
            self.logger.warning(
                "Failed to estimate canvas history memory: %s",
                error,
            )
            return 0.0, 0.0

    def _cached_entry_memory(
        self,
        entry: dict[str, Any],
    ) -> tuple[float, float]:
        entry_id = id(entry)
        cached = self._memory_cache.get(entry_id)
        if cached is not None:
            return cached
        cached = self._estimate_entry_memory(entry)
        self._memory_cache[entry_id] = cached
        return cached

    def _estimate_entry_memory(
        self,
        entry: dict[str, Any],
    ) -> tuple[float, float]:
        """Estimate memory for one history entry in megabytes."""
        vram_mb = 0.0
        ram_mb = 0.0
        try:
            entry_type = entry.get("type", "")
            if entry_type == "image":
                vram_mb, ram_mb = self._estimate_image_entry_memory(entry)
            elif entry_type in ("create", "delete", "reorder"):
                vram_mb, ram_mb = self._estimate_layer_entry_memory(entry)
        except Exception as error:
            self.logger.debug("Failed to estimate entry memory: %s", error)
        return vram_mb, ram_mb

    def _estimate_image_entry_memory(
        self,
        entry: dict[str, Any],
    ) -> tuple[float, float]:
        before = entry.get("before", {})
        after = entry.get("after", {})
        vram_mb = self._estimate_image_memory_fast(
            before.get("image"),
            before.get("image_width"),
            before.get("image_height"),
        )
        vram_mb += self._estimate_image_memory_fast(
            after.get("image"),
            after.get("image_width"),
            after.get("image_height"),
        )
        vram_mb += self._estimate_image_memory(before.get("mask"))
        vram_mb += self._estimate_image_memory(after.get("mask"))
        return vram_mb, vram_mb * 0.5

    def _estimate_layer_entry_memory(
        self,
        entry: dict[str, Any],
    ) -> tuple[float, float]:
        layers = [
            *entry.get("layers_before", []),
            *entry.get("layers_after", []),
        ]
        vram_mb = sum(
            self._estimate_layer_snapshot_memory(layer_data)
            for layer_data in layers
        )
        return vram_mb, vram_mb * 0.3

    def _estimate_image_memory_fast(
        self,
        image_data: bytes | None,
        width: int | None,
        height: int | None,
    ) -> float:
        """Estimate VRAM usage using pre-extracted dimensions."""
        if not image_data:
            return 0.0
        if width is not None and height is not None:
            return (width * height * 4) / (1024 * 1024)
        return self._estimate_image_memory(image_data)

    def _estimate_image_memory(self, image_data: bytes | None) -> float:
        """Estimate VRAM usage for binary image data."""
        if not image_data:
            return 0.0
        try:
            if image_data.startswith(b"AIRAW1") and len(image_data) >= 14:
                width = int.from_bytes(image_data[6:10], "big")
                height = int.from_bytes(image_data[10:14], "big")
                return (width * height * 4) / (1024 * 1024)
            return len(image_data) / (1024 * 1024)
        except Exception:
            return 4.0

    def _estimate_layer_snapshot_memory(
        self,
        layer_data: dict[str, Any],
    ) -> float:
        """Estimate VRAM usage for a serialized layer snapshot."""
        try:
            settings = layer_data.get("drawing_pad_settings", {})
            vram_mb = self._estimate_image_memory(settings.get("image"))
            vram_mb += self._estimate_image_memory(settings.get("mask"))
            return vram_mb
        except Exception:
            return 0.0

    def get_history_summary(
        self,
        scene: CanvasSceneLike,
    ) -> dict[str, float | int]:
        """Return a summary of canvas history memory usage."""
        vram_gb, ram_gb = self.estimate_history_memory(scene)
        return {
            "undo_count": len(scene.undo_history),
            "redo_count": len(scene.redo_history),
            "total_entries": len(scene.undo_history) + len(scene.redo_history),
            "vram_gb": vram_gb,
            "ram_gb": ram_gb,
            "vram_mb": vram_gb * 1024,
            "ram_mb": ram_gb * 1024,
        }

    def clear_cache(self) -> None:
        """Clear the memory estimation cache."""
        self._memory_cache.clear()
        self.logger.debug("Canvas memory estimation cache cleared")