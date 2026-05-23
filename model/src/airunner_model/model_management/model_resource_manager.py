"""Model-owned resource manager for model allocation state."""

from __future__ import annotations

import logging
import subprocess
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Tuple

from airunner_model.model_management.canvas_memory_tracker import (
    CanvasMemoryTracker,
)
from airunner_model.model_management.hardware_profiler import HardwareProfile
from airunner_model.model_management.hardware_profiler import HardwareProfiler
from airunner_model.model_management.memory_allocator import MemoryAllocator
from airunner_model.model_management.mixins.memory_tracking_mixin import (
    MemoryTrackingMixin,
)
from airunner_model.model_management.mixins.model_loading_mixin import (
    ModelLoadingMixin,
)
from airunner_model.model_management.mixins.model_selection_mixin import (
    ModelSelectionMixin,
)
from airunner_model.model_management.mixins.model_state_mixin import (
    ModelStateMixin,
)
from airunner_model.model_management.model_registry import ModelRegistry
from airunner_model.model_management.quantization_strategy import (
    QuantizationStrategy,
)
from airunner_model.model_management.types import ModelState

UnloadModelCallback = Callable[[str, str], None]


class ModelResourceManager(
    ModelStateMixin,
    MemoryTrackingMixin,
    ModelSelectionMixin,
    ModelLoadingMixin,
):
    """Central coordinator for model state and allocation policy."""

    _instance = None

    def __new__(cls, *args: object, **kwargs: object):
        del args, kwargs
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        *,
        logger: Optional[Any] = None,
        unload_model_callback: Optional[UnloadModelCallback] = None,
        hardware_profiler: Optional[HardwareProfiler] = None,
        quantization_strategy: Optional[QuantizationStrategy] = None,
        registry: Optional[ModelRegistry] = None,
        memory_allocator: Optional[MemoryAllocator] = None,
        canvas_memory_tracker: Optional[CanvasMemoryTracker] = None,
    ) -> None:
        if hasattr(self, "_initialized"):
            return
        self.logger = logger or logging.getLogger(__name__)
        self._unload_model_callback = unload_model_callback
        self.hardware_profiler = hardware_profiler or HardwareProfiler()
        self.quantization_strategy = (
            quantization_strategy or QuantizationStrategy()
        )
        self.registry = registry or ModelRegistry()
        hardware = self.hardware_profiler.get_profile()
        self.memory_allocator = memory_allocator or MemoryAllocator(hardware)
        self.canvas_memory_tracker = (
            canvas_memory_tracker or CanvasMemoryTracker()
        )
        self._model_states: Dict[str, ModelState] = {}
        self._model_types: Dict[str, str] = {}
        self._canvas_history_vram_gb = 0.0
        self._canvas_history_ram_gb = 0.0
        self._external_apps_vram_gb = 0.0
        self._initialized = True
        self._log_hardware_profile(hardware)

    def _log_hardware_profile(self, hardware: HardwareProfile) -> None:
        """Log the detected hardware profile."""
        self.logger.debug("Hardware Profile:")
        self.logger.debug(
            "  VRAM: %.1fGB / %.1fGB",
            hardware.available_vram_gb,
            hardware.total_vram_gb,
        )
        self.logger.debug(
            "  RAM: %.1fGB / %.1fGB",
            hardware.available_ram_gb,
            hardware.total_ram_gb,
        )
        self.logger.debug("  GPU: %s", hardware.device_name or "None")
        self.logger.debug("  CUDA: %s", hardware.cuda_available)

    def check_memory_pressure(self) -> bool:
        """Return whether the allocator reports memory pressure."""
        return self.memory_allocator.is_under_memory_pressure()

    def can_perform_operation(
        self,
        model_type: str,
        model_id: str | None = None,
    ) -> Tuple[bool, str]:
        """Return whether one model operation should be allowed."""
        blocked = self._blocked_by_active_model()
        if blocked is not None:
            return blocked
        active = self.get_active_models()
        if not active:
            return True, "OK"
        available_vram = self.hardware_profiler.get_profile().available_vram_gb
        minimum_vram = self._minimum_vram_for(model_id)
        if available_vram >= minimum_vram:
            return True, "OK"
        active_models = ", ".join(
            f"{model.model_type.upper()}" for model in active
        )
        return False, (
            f"Insufficient VRAM for {model_type.upper()}.\n\n"
            f"Required: ~{minimum_vram:.1f}GB\n"
            f"Available: {available_vram:.1f}GB\n"
            f"Active models: {active_models}\n\n"
            f"Please close other models first."
        )

    def _blocked_by_active_model(self) -> Tuple[bool, str] | None:
        """Return one blocking reason when another model is busy."""
        active = self.get_active_models()
        for state, message in (
            (ModelState.LOADING, "{name} is currently loading. Please wait."),
            (
                ModelState.UNLOADING,
                "{name} is currently unloading. Please wait.",
            ),
            (ModelState.BUSY, "{name} is currently processing. Please wait."),
        ):
            match = next((model for model in active if model.state is state), None)
            if match is not None:
                return False, message.format(name=match.model_type.upper())
        return None

    def _minimum_vram_for(self, model_id: str | None) -> float:
        """Return the minimum VRAM estimate for one model selection."""
        if not model_id:
            return 4.0
        metadata = self.registry.get_model(model_id)
        if metadata is None:
            return 4.0
        return metadata.min_vram_gb

    def _unload_model_for_swap(self, model_id: str, model_type: str) -> None:
        """Delegate one unload operation to the configured callback."""
        callback = self._unload_model_callback
        if callback is None:
            raise RuntimeError("Model swap unload callback is not configured")
        callback(model_id, model_type)

    def detect_external_vram_usage(self) -> float:
        """Return VRAM usage attributed to external applications."""
        for command in (
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            ["rocm-smi", "--showmeminfo", "vram", "--csv"],
        ):
            value = self._run_vram_query(command)
            if value is not None:
                return value
        return 0.0

    def _run_vram_query(self, command: list[str]) -> float | None:
        """Run one VRAM usage command and parse its first value."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if result.returncode != 0:
            return None
        if command[0] == "nvidia-smi":
            return self._parse_nvidia_vram_usage(result.stdout)
        return self._parse_rocm_vram_usage(result.stdout)

    @staticmethod
    def _parse_nvidia_vram_usage(output: str) -> float | None:
        """Parse VRAM usage reported by `nvidia-smi`."""
        try:
            used_mb = float(output.strip().split("\n")[0])
        except (IndexError, ValueError):
            return None
        return used_mb / 1024.0

    @staticmethod
    def _parse_rocm_vram_usage(output: str) -> float | None:
        """Parse VRAM usage reported by `rocm-smi`."""
        for line in output.strip().split("\n"):
            if "used" not in line.lower():
                continue
            for part in line.split(","):
                lower_part = part.lower()
                if "mb" not in lower_part and "gb" not in lower_part:
                    continue
                value = "".join(
                    character
                    for character in part
                    if character.isdigit() or character == "."
                )
                if not value:
                    continue
                parsed = float(value)
                if "mb" in lower_part:
                    return parsed / 1024.0
                return parsed
        return None


__all__ = ["ModelResourceManager", "ModelState"]