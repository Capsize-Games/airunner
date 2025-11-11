"""
Canvas history memory tracking for model resource management.

Estimates VRAM and RAM usage by canvas undo/redo history.
"""

from typing import TYPE_CHECKING

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

if TYPE_CHECKING:
    from airunner.components.art.gui.widgets.canvas.custom_scene import (
        CustomScene,
    )


class CanvasMemoryTracker:
    """Track memory usage of canvas history."""

    def __init__(self):
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        # Cache memory estimates by entry ID to avoid recalculating
        self._memory_cache: dict[int, tuple[float, float]] = {}

    def estimate_history_memory(
        self, scene: "CustomScene"
    ) -> tuple[float, float]:
        """
        Estimate VRAM and RAM usage by canvas history.

        Args:
            scene: CustomScene instance with undo/redo history

        Returns:
            Tuple of (vram_gb, ram_gb)
        """
        try:
            total_vram_mb = 0.0
            total_ram_mb = 0.0

            # Estimate from undo history with caching
            for entry in scene.undo_history:
                entry_id = id(entry)
                if entry_id not in self._memory_cache:
                    vram, ram = self._estimate_entry_memory(entry)
                    self._memory_cache[entry_id] = (vram, ram)
                else:
                    vram, ram = self._memory_cache[entry_id]
                total_vram_mb += vram
                total_ram_mb += ram

            # Estimate from redo history with caching
            for entry in scene.redo_history:
                entry_id = id(entry)
                if entry_id not in self._memory_cache:
                    vram, ram = self._estimate_entry_memory(entry)
                    self._memory_cache[entry_id] = (vram, ram)
                else:
                    vram, ram = self._memory_cache[entry_id]
                total_vram_mb += vram
                total_ram_mb += ram

            # Convert MB to GB
            return total_vram_mb / 1024.0, total_ram_mb / 1024.0

        except Exception as e:
            self.logger.warning(
                f"Failed to estimate canvas history memory: {e}"
            )
            return 0.0, 0.0

    def _estimate_entry_memory(self, entry: dict) -> tuple[float, float]:
        """
        Estimate memory for a single history entry.

        Returns:
            Tuple of (vram_mb, ram_mb)
        """
        vram_mb = 0.0
        ram_mb = 0.0

        try:
            entry_type = entry.get("type", "")

            # Image history entries contain before/after image data
            if entry_type == "image":
                before = entry.get("before", {})
                after = entry.get("after", {})

                # Use pre-extracted dimensions if available (faster)
                vram_mb += self._estimate_image_memory_fast(
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

                # Images are stored in VRAM (GPU textures) and RAM (CPU buffers)
                ram_mb = vram_mb * 0.5  # Rough estimate: 50% overhead in RAM

            # Layer structure changes (create/delete/reorder)
            elif entry_type in ("create", "delete", "reorder"):
                layers_before = entry.get("layers_before", [])
                layers_after = entry.get("layers_after", [])

                for layer_data in layers_before + layers_after:
                    # Estimate layer snapshot memory
                    vram_mb += self._estimate_layer_snapshot_memory(layer_data)

                ram_mb = vram_mb * 0.3  # Layer metadata is lighter

        except Exception as e:
            self.logger.debug(f"Failed to estimate entry memory: {e}")

        return vram_mb, ram_mb

    def _estimate_image_memory_fast(
        self,
        image_data: bytes | None,
        width: int | None,
        height: int | None,
    ) -> float:
        """
        Estimate VRAM usage using pre-extracted dimensions (fast path).

        Args:
            image_data: Binary image data (for validation)
            width: Pre-extracted image width
            height: Pre-extracted image height

        Returns:
            Estimated VRAM in MB
        """
        if not image_data:
            return 0.0

        # Fast path: use pre-extracted dimensions
        if width is not None and height is not None:
            pixels = width * height
            bytes_size = pixels * 4  # RGBA = 4 bytes per pixel
            return bytes_size / (1024 * 1024)

        # Fallback to parsing binary
        return self._estimate_image_memory(image_data)

    def _estimate_image_memory(self, image_data: bytes | None) -> float:
        """
        Estimate VRAM usage for image data.

        Args:
            image_data: Binary image data (AIRAW1 format or None)

        Returns:
            Estimated VRAM in MB
        """
        if not image_data:
            return 0.0

        try:
            # AIRAW1 format: b'AIRAW1' + width(4) + height(4) + rgba_bytes
            if isinstance(image_data, bytes) and image_data.startswith(
                b"AIRAW1"
            ):
                # Header is 14 bytes: 'AIRAW1' (6) + width (4) + height (4)
                if len(image_data) < 14:
                    return 0.0

                width = int.from_bytes(image_data[6:10], "big")
                height = int.from_bytes(image_data[10:14], "big")

                # RGBA = 4 bytes per pixel
                pixels = width * height
                bytes_size = pixels * 4

                # Convert to MB
                return bytes_size / (1024 * 1024)
            else:
                # Fallback: use actual data size
                return len(image_data) / (1024 * 1024)

        except Exception:
            # Fallback: assume small image if parsing fails
            return 4.0  # 4MB default estimate

    def _estimate_layer_snapshot_memory(self, layer_data: dict) -> float:
        """
        Estimate VRAM for a layer snapshot.

        Args:
            layer_data: Layer snapshot dictionary

        Returns:
            Estimated VRAM in MB
        """
        vram_mb = 0.0

        try:
            # Layer snapshots may contain drawing_pad_settings with image/mask
            settings = layer_data.get("drawing_pad_settings", {})
            vram_mb += self._estimate_image_memory(settings.get("image"))
            vram_mb += self._estimate_image_memory(settings.get("mask"))

        except Exception:
            pass

        return vram_mb

    def get_history_summary(self, scene: "CustomScene") -> dict:
        """
        Get summary of canvas history memory usage.

        Args:
            scene: CustomScene instance

        Returns:
            Dictionary with memory statistics
        """
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
        """Clear the memory estimation cache.

        Call this when canvas history is cleared or major changes occur.
        """
        self._memory_cache.clear()
        self.logger.debug("Canvas memory estimation cache cleared")
