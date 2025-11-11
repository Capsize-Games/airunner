from typing import Dict, Tuple

from airunner.components.model_management.types import (
    ModelState,
)
from airunner.components.model_management.hardware_profiler import (
    HardwareProfiler,
    HardwareProfile,
)
from airunner.components.model_management.quantization_strategy import (
    QuantizationStrategy,
)
from airunner.components.model_management.model_registry import (
    ModelRegistry,
)
from airunner.components.model_management.memory_allocator import (
    MemoryAllocator,
)
from airunner.components.model_management.mixins import (
    ModelStateMixin,
    MemoryTrackingMixin,
    ModelSelectionMixin,
    ModelLoadingMixin,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.application.signal_mediator import SignalMediator


class ModelResourceManager(
    ModelStateMixin,
    MemoryTrackingMixin,
    ModelSelectionMixin,
    ModelLoadingMixin,
):
    """Central coordinator for all model resource operations.

    This class uses mixins to organize functionality:
    - ModelStateMixin: Model lifecycle state management
    - MemoryTrackingMixin: Non-model memory allocation tracking
    - ModelSelectionMixin: Best model selection for hardware
    - ModelLoadingMixin: Model loading and swapping operations
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self.signal_mediator = SignalMediator()
        self.hardware_profiler = HardwareProfiler()
        self.quantization_strategy = QuantizationStrategy()
        self.registry = ModelRegistry()

        hardware = self.hardware_profiler.get_profile()
        self.memory_allocator = MemoryAllocator(hardware)

        # Canvas memory tracker (singleton, reused for caching)
        from airunner.components.model_management.canvas_memory_tracker import (
            CanvasMemoryTracker,
        )

        self.canvas_memory_tracker = CanvasMemoryTracker()

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

    def check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure."""
        return self.memory_allocator.is_under_memory_pressure()

    def _emit_signal(self, signal_code, data):
        """Emit signal via SignalMediator."""
        self.signal_mediator.emit(signal_code, data)

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

        # Check if there are conflicting models loaded
        # Block if trying to load a different type while another is loaded
        if active:
            # Get list of active model types (excluding the one we're trying to load)
            set(m.model_type for m in active)

            # If there are any active models, check if we have enough VRAM
            hardware = self.hardware_profiler.get_profile()
            available_vram = hardware.available_vram_gb

            # Estimate VRAM needed (conservative estimate if model not in registry)
            if model_id:
                metadata = self.registry.get_model(model_id)
                min_required = (
                    metadata.min_vram_gb if metadata else 4.0
                )  # Default 4GB for unregistered models
            else:
                min_required = 4.0  # Default estimate

            if available_vram < min_required:
                active_models_str = ", ".join(
                    [f"{m.model_type.upper()}" for m in active]
                )
                return False, (
                    f"Insufficient VRAM for {model_type.upper()}.\n\n"
                    f"Required: ~{min_required:.1f}GB\n"
                    f"Available: {available_vram:.1f}GB\n"
                    f"Active models: {active_models_str}\n\n"
                    f"Please close other models first."
                )

        return True, "OK"

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
