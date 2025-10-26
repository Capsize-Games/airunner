import logging
from enum import Enum
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass

from airunner.components.model_management.hardware_profiler import (
    HardwareProfiler,
    HardwareProfile,
)
from airunner.components.model_management.quantization_strategy import (
    QuantizationStrategy,
    QuantizationLevel,
)
from airunner.components.model_management.model_registry import (
    ModelRegistry,
    ModelMetadata,
    ModelProvider,
    ModelType,
)
from airunner.components.model_management.memory_allocator import (
    MemoryAllocator,
)
from airunner.utils.application.signal_mediator import SignalMediator


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
        self.signal_mediator = SignalMediator()
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
        auto_swap: bool = True,
    ) -> dict:
        """
        Prepare resources for model loading.

        Args:
            model_id: Identifier for the model
            model_type: Type of model (llm, text_to_image, tts, stt)
            preferred_quantization: Preferred quantization level
            auto_swap: Whether to automatically unload conflicting models

        Returns:
            Dict with keys:
            - can_load: bool
            - reason: str (if can_load is False)
            - metadata: ModelMetadata (if available)
            - quantization: QuantizationConfig (if applicable)
            - allocation: MemoryAllocation (if successful)
            - swapped_models: List[str] (models that were unloaded)
        """
        # Set loading state
        self.set_model_state(model_id, ModelState.LOADING, model_type)

        metadata = self.registry.get_model(model_id)
        if not metadata:
            self.logger.warning(
                f"Model {model_id} not in registry - checking for conflicts anyway"
            )
            # Even if not in registry, check if there are conflicting models loaded
            # and attempt to swap if auto_swap is enabled
            if auto_swap:
                # Check if any models are currently loaded
                active_models = self.get_active_models()
                if active_models:
                    self.logger.info(
                        f"Found {len(active_models)} active models while loading unregistered model"
                    )
                    # Attempt to swap to make room
                    swap_result = self.request_model_swap(model_id, model_type)
                    if (
                        swap_result["success"]
                        and swap_result["unloaded_models"]
                    ):
                        self.logger.info(
                            f"Auto-swapped {len(swap_result['unloaded_models'])} models for unregistered model"
                        )
                        return {
                            "can_load": True,
                            "reason": "Model not in registry but made room via auto-swap",
                            "swapped_models": swap_result["unloaded_models"],
                        }

            # Allow load but warn
            return {
                "can_load": True,
                "reason": "Model not in registry - no validation performed",
                "swapped_models": [],
            }

        hardware = self.hardware_profiler.get_profile()
        quantization = self.quantization_strategy.select_quantization(
            metadata.size_gb, hardware, preferred_quantization
        )

        # Try to allocate memory
        allocation = self.memory_allocator.allocate(model_id, quantization)

        # If allocation fails and auto_swap is enabled, try swapping models
        if not allocation and auto_swap:
            self.logger.info(
                f"Insufficient memory for {model_id}, attempting auto-swap"
            )
            swap_result = self.request_model_swap(model_id, model_type)

            if swap_result["success"]:
                self.logger.info(
                    f"Auto-swap successful: unloaded {len(swap_result['unloaded_models'])} models"
                )
                # Try allocation again after swap
                allocation = self.memory_allocator.allocate(
                    model_id, quantization
                )

                if allocation:
                    self.logger.info(
                        f"Prepared {metadata.name} after auto-swap: {quantization.description}"
                    )
                    return {
                        "can_load": True,
                        "metadata": metadata,
                        "quantization": quantization,
                        "allocation": allocation,
                        "swapped_models": swap_result["unloaded_models"],
                    }

        if not allocation:
            self.set_model_state(model_id, ModelState.UNLOADED)
            return {
                "can_load": False,
                "reason": "Insufficient memory even after attempting model swap",
                "metadata": metadata,
                "quantization": quantization,
                "swapped_models": [],
            }

        self.logger.info(
            f"Prepared {metadata.name}: {quantization.description}"
        )
        return {
            "can_load": True,
            "metadata": metadata,
            "quantization": quantization,
            "allocation": allocation,
            "swapped_models": [],
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

    def request_model_swap(
        self, target_model_id: str, target_model_type: str
    ) -> Dict[str, Any]:
        """
        Request automatic model swapping to make room for target model.

        Returns:
            Dict with keys:
            - success: bool - whether swap was successful
            - unloaded_models: List[str] - models that were unloaded
            - reason: str - explanation if swap failed
        """
        # Get models that need to be unloaded
        models_to_unload = self._determine_models_to_unload(
            target_model_id, target_model_type
        )

        if not models_to_unload:
            return {
                "success": True,
                "unloaded_models": [],
                "reason": "No models need to be unloaded",
            }

        # Track which models were successfully unloaded
        unloaded = []

        for model_id in models_to_unload:
            model_type = self._model_types.get(model_id, "unknown")
            self.logger.info(
                f"Auto-swapping: Unloading {model_type} model {model_id}"
            )

            try:
                # CRITICAL: Use synchronous API calls instead of async signals
                # This ensures models are ACTUALLY unloaded before we try to load the new one
                # Async signals were causing race conditions where SD would try to load
                # before LLM was fully unloaded, leading to VRAM exhaustion

                if model_type == "llm":
                    # Import here to avoid circular dependency
                    from airunner.components.llm.managers.llm_model_manager import (
                        LLMModelManager,
                    )

                    manager = LLMModelManager()
                    manager.unload()
                    self.logger.info(
                        "LLM unloaded synchronously for auto-swap"
                    )

                elif model_type == "text_to_image":
                    # SD unload via API
                    from airunner.components.application.api.api import API

                    api = API()
                    api.art.unload()
                    self.logger.info("SD unloaded synchronously for auto-swap")

                elif model_type == "tts":
                    from airunner.enums import SignalCode

                    self._emit_signal(SignalCode.TTS_DISABLE_SIGNAL, {})

                elif model_type == "stt":
                    from airunner.enums import SignalCode

                    self._emit_signal(SignalCode.STT_DISABLE_SIGNAL, {})

                unloaded.append(model_id)

            except Exception as e:
                self.logger.error(
                    f"Failed to unload {model_id}: {e}", exc_info=True
                )
                return {
                    "success": False,
                    "unloaded_models": unloaded,
                    "reason": f"Failed to unload {model_id}: {str(e)}",
                }

        return {
            "success": True,
            "unloaded_models": unloaded,
            "reason": f"Successfully unloaded {len(unloaded)} models",
        }

    def _determine_models_to_unload(
        self, target_model_id: str, target_model_type: str
    ) -> List[str]:
        """
        Determine which models should be unloaded to make room for target model.

        Strategy:
        1. Never unload models in LOADING or BUSY state
        2. Prioritize unloading models based on type hierarchy:
           - SD has highest priority (art generation)
           - LLM has medium priority (chat)
           - TTS/STT have lowest priority (auxiliary)
        3. Unload lowest priority models first
        4. Stop when sufficient memory is available
        """
        # Define model priority (higher = more important, keep loaded)
        priority_map = {
            "text_to_image": 3,  # Highest priority - keep SD loaded if possible
            "llm": 2,  # Medium priority
            "tts": 1,  # Low priority
            "stt": 1,  # Low priority
        }

        target_priority = priority_map.get(target_model_type, 2)

        # Get all loaded models that can be unloaded
        candidates = []
        for model_id, state in self._model_states.items():
            if state not in (ModelState.LOADED, ModelState.UNLOADED):
                # Skip models that are loading or busy
                continue

            if state == ModelState.UNLOADED:
                continue

            model_type = self._model_types.get(model_id, "unknown")
            model_priority = priority_map.get(model_type, 2)

            # Only unload models with lower or equal priority
            if model_priority <= target_priority:
                allocation = self.memory_allocator._allocations.get(model_id)
                if allocation:
                    candidates.append(
                        (
                            model_id,
                            model_type,
                            model_priority,
                            allocation.vram_allocated_gb,
                        )
                    )

        # Sort by priority (lowest first), then by VRAM usage (largest first)
        candidates.sort(key=lambda x: (x[2], -x[3]))

        # Determine how much memory we need
        # For now, we'll unload all conflicting lower-priority models
        # In the future, we could be smarter and only unload what's needed

        models_to_unload = [model_id for model_id, _, _, _ in candidates]

        return models_to_unload

    def _emit_signal(self, signal_code, data):
        """Emit signal via SignalMediator."""
        self.signal_mediator.emit(signal_code, data)

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

            # Try to get allocation info, but still report model even without it
            # (unregistered models may not have allocations)
            allocation = self.memory_allocator._allocations.get(model_id)

            active_models.append(
                ActiveModelInfo(
                    model_id=model_id,
                    model_type=self._model_types.get(model_id, "unknown"),
                    state=state,
                    vram_allocated_gb=(
                        allocation.vram_allocated_gb if allocation else 0.0
                    ),
                    ram_allocated_gb=(
                        allocation.ram_allocated_gb if allocation else 0.0
                    ),
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
