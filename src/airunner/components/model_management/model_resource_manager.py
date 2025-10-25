import logging
from enum import Enum
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

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


class ModelState(Enum):
    """Model lifecycle states."""

    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    UNLOADING = "unloading"
    BUSY = "busy"  # Actively generating/processing


@dataclass
class ActiveModelInfo:
    """Information about an active model."""

    model_id: str
    model_type: str
    state: ModelState
    vram_allocated_gb: float
    ram_allocated_gb: float
    can_unload: bool


@dataclass
class MemoryAllocationBreakdown:
    """Breakdown of memory allocation by category."""

    models_vram_gb: float
    canvas_history_vram_gb: float
    canvas_history_ram_gb: float
    system_reserve_vram_gb: float
    system_reserve_ram_gb: float
    external_apps_vram_gb: float
    total_available_vram_gb: float
    total_available_ram_gb: float


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

        # Model state tracking
        self._model_states: Dict[str, ModelState] = {}
        self._model_types: Dict[str, str] = {}

        # Memory allocation tracking
        self._canvas_history_vram_gb = 0.0
        self._canvas_history_ram_gb = 0.0
        self._external_apps_vram_gb = 0.0

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
        # Set loading state
        self.set_model_state(model_id, ModelState.LOADING, model_type)

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
            self.set_model_state(model_id, ModelState.UNLOADED)
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

    def model_loaded(self, model_id: str) -> None:
        """Mark model as loaded successfully."""
        self.set_model_state(model_id, ModelState.LOADED)

    def model_busy(self, model_id: str) -> None:
        """Mark model as busy (generating/processing)."""
        self.set_model_state(model_id, ModelState.BUSY)

    def model_ready(self, model_id: str) -> None:
        """Mark model as ready (finished processing)."""
        self.set_model_state(model_id, ModelState.LOADED)

    def cleanup_model(self, model_id: str, model_type: str = "llm") -> None:
        """Cleanup resources after model unloading."""
        self.set_model_state(model_id, ModelState.UNLOADING, model_type)
        self.memory_allocator.deallocate(model_id)
        self.set_model_state(model_id, ModelState.UNLOADED)

    def check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure."""
        return self.memory_allocator.is_under_memory_pressure()

    def set_model_state(
        self, model_id: str, state: ModelState, model_type: str = None
    ) -> None:
        """Update model state."""
        self._model_states[model_id] = state
        if model_type:
            self._model_types[model_id] = model_type
        self.logger.debug(f"Model {model_id} state: {state.value}")

    def get_model_state(self, model_id: str) -> ModelState:
        """Get current model state."""
        return self._model_states.get(model_id, ModelState.UNLOADED)

    def get_active_models(self) -> List[ActiveModelInfo]:
        """Get list of all active models with their states."""
        active_models = []

        for model_id, state in self._model_states.items():
            if state == ModelState.UNLOADED:
                continue

            allocation = self.memory_allocator._allocations.get(model_id)
            if allocation:
                active_models.append(
                    ActiveModelInfo(
                        model_id=model_id,
                        model_type=self._model_types.get(model_id, "unknown"),
                        state=state,
                        vram_allocated_gb=allocation.vram_allocated_gb,
                        ram_allocated_gb=allocation.ram_allocated_gb,
                        can_unload=(state == ModelState.LOADED),
                    )
                )

        return active_models

    def can_perform_operation(
        self, model_type: str, model_id: str = None
    ) -> Tuple[bool, str]:
        """
        Check if a model operation can be performed.

        Returns:
            Tuple of (can_perform, reason)
        """
        active = self.get_active_models()

        # Check if any model is loading
        loading = [m for m in active if m.state == ModelState.LOADING]
        if loading:
            return (
                False,
                f"{loading[0].model_type.upper()} is currently loading. Please wait.",
            )

        # Check if any model is unloading
        unloading = [m for m in active if m.state == ModelState.UNLOADING]
        if unloading:
            return (
                False,
                f"{unloading[0].model_type.upper()} is currently unloading. Please wait.",
            )

        # Check if any model is busy (generating/processing)
        busy = [m for m in active if m.state == ModelState.BUSY]
        if busy:
            return (
                False,
                f"{busy[0].model_type.upper()} is currently processing. Please wait.",
            )

        # Check if we have enough VRAM for the requested model
        if model_id:
            metadata = self.registry.get_model(model_id)
            if metadata:
                hardware = self.hardware_profiler.get_profile()
                available_vram = self._get_available_vram_with_allocations()

                # Estimate required VRAM (will be refined during prepare_model_loading)
                min_required = metadata.min_vram_gb

                if available_vram < min_required:
                    active_models_str = ", ".join(
                        [
                            f"{m.model_type.upper()} ({m.vram_allocated_gb:.1f}GB)"
                            for m in active
                        ]
                    )
                    return False, (
                        f"Insufficient VRAM for {model_type.upper()}.\n\n"
                        f"Required: {min_required:.1f}GB\n"
                        f"Available: {available_vram:.1f}GB\n"
                        f"Active models: {active_models_str}"
                    )

        return True, "OK"

    def _get_available_vram_with_allocations(self) -> float:
        """Get available VRAM accounting for all allocations."""
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

    def update_canvas_history_allocation(
        self, vram_gb: float = 0.0, ram_gb: float = 0.0
    ) -> None:
        """Update canvas history memory allocation."""
        self._canvas_history_vram_gb = vram_gb
        self._canvas_history_ram_gb = ram_gb
        self.logger.debug(
            f"Canvas history allocation updated: "
            f"VRAM={vram_gb:.2f}GB, RAM={ram_gb:.2f}GB"
        )

    def update_external_apps_allocation(self, vram_gb: float = 0.0) -> None:
        """Update external application VRAM usage."""
        self._external_apps_vram_gb = vram_gb
        self.logger.debug(f"External apps VRAM usage: {vram_gb:.2f}GB")

    def get_memory_allocation_breakdown(self) -> MemoryAllocationBreakdown:
        """Get detailed breakdown of memory allocation."""
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

    def detect_external_vram_usage(self) -> float:
        """
        Detect VRAM usage by external applications.

        Uses nvidia-smi for NVIDIA GPUs, rocm-smi for AMD.
        Returns 0.0 if detection fails or GPU not found.
        """
        import subprocess

        try:
            # Try NVIDIA first
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.used",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if result.returncode == 0:
                # nvidia-smi returns MB
                used_mb = float(result.stdout.strip().split("\n")[0])
                return used_mb / 1024.0  # Convert to GB
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass

        try:
            # Try AMD ROCm
            result = subprocess.run(
                ["rocm-smi", "--showmeminfo", "vram", "--csv"],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if result.returncode == 0:
                # Parse ROCm output (format varies)
                # This is a simplified parser
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if "used" in line.lower():
                        parts = line.split(",")
                        for part in parts:
                            if "mb" in part.lower() or "gb" in part.lower():
                                value_str = "".join(
                                    c for c in part if c.isdigit() or c == "."
                                )
                                if value_str:
                                    value = float(value_str)
                                    if "mb" in part.lower():
                                        return value / 1024.0
                                    return value
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass

        return 0.0
