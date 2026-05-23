"""Behavior tests for model-owned model-management helpers."""

from __future__ import annotations

from airunner_model.model_management.canvas_memory_tracker import (
    CanvasMemoryTracker,
)
from airunner_model.model_management.hardware_profiler import HardwareProfile
from airunner_model.model_management.memory_allocator import MemoryAllocator
from airunner_model.model_management.mixins.model_loading_mixin import (
    ModelLoadingMixin,
)
from airunner_model.model_management.mixins.memory_tracking_mixin import (
    MemoryTrackingMixin,
)
from airunner_model.model_management.mixins.model_selection_mixin import (
    ModelSelectionMixin,
)
from airunner_model.model_management.mixins.model_state_mixin import (
    ModelStateMixin,
)
from airunner_model.model_management.model_resource_manager import (
    ModelResourceManager,
)
from airunner_model.model_management.model_registry import ModelRegistry
from airunner_model.model_management.model_registry import ModelMetadata
from airunner_model.model_management.model_registry import ModelProvider
from airunner_model.model_management.model_registry import ModelType
from airunner_model.model_management.quantization_strategy import (
    QuantizationConfig,
)
from airunner_model.model_management.quantization_strategy import (
    QuantizationLevel,
)
from airunner_model.model_management.quantization_strategy import (
    QuantizationStrategy,
)
from airunner_model.model_management.types import ModelState


class _Scene:
    def __init__(self, undo_history: list[dict], redo_history: list[dict]) -> None:
        self.undo_history = undo_history
        self.redo_history = redo_history


def _airaw_bytes(width: int, height: int) -> bytes:
    header = b"AIRAW1" + width.to_bytes(4, "big") + height.to_bytes(4, "big")
    return header + (b"\0" * width * height * 4)


def _hardware_profile(available_vram_gb: float) -> HardwareProfile:
    return HardwareProfile(
        total_vram_gb=24.0,
        available_vram_gb=available_vram_gb,
        total_ram_gb=64.0,
        available_ram_gb=48.0,
        cuda_available=True,
        cuda_compute_capability=(8, 6),
        device_name="Test GPU",
        cpu_count=16,
        platform="Linux",
    )


class _DummyResourceManager(
    ModelStateMixin,
    MemoryTrackingMixin,
    ModelSelectionMixin,
):
    def __init__(self) -> None:
        self.logger = _Logger()
        self.hardware_profiler = _Profiler(_hardware_profile(available_vram_gb=16.0))
        self.memory_allocator = MemoryAllocator(_hardware_profile(16.0))
        self.registry = _Registry()
        self._model_states: dict[str, ModelState] = {}
        self._model_types: dict[str, str] = {}
        self._canvas_history_vram_gb = 0.0
        self._canvas_history_ram_gb = 0.0
        self._external_apps_vram_gb = 0.0


class _SwapLoader(ModelLoadingMixin, ModelStateMixin):
    def __init__(self) -> None:
        self.logger = _Logger()
        self.hardware_profiler = _Profiler(_hardware_profile(available_vram_gb=16.0))
        self.memory_allocator = MemoryAllocator(_hardware_profile(16.0))
        self.quantization_strategy = QuantizationStrategy()
        self.registry = _SwapRegistry()
        self._model_states: dict[str, ModelState] = {}
        self._model_types: dict[str, str] = {"loaded-model": "tts"}
        self.unloaded: list[tuple[str, str]] = []

    def _unload_model_for_swap(self, model_id: str, model_type: str) -> None:
        self.unloaded.append((model_id, model_type))


class _PureModelResourceManager(ModelResourceManager):
    _instance = None


class _Logger:
    def debug(self, *args, **kwargs) -> None:
        del args, kwargs

    def info(self, *args, **kwargs) -> None:
        del args, kwargs

    def warning(self, *args, **kwargs) -> None:
        del args, kwargs

    def error(self, *args, **kwargs) -> None:
        del args, kwargs


class _Profiler:
    def __init__(self, profile: HardwareProfile) -> None:
        self._profile = profile

    def get_profile(self) -> HardwareProfile:
        return self._profile


class _Registry:
    def list_models(
        self,
        provider: ModelProvider,
        model_type: ModelType,
    ) -> list[ModelMetadata]:
        del provider, model_type
        return [
            ModelMetadata(
                name="Small",
                provider=ModelProvider.LLAMA,
                model_type=ModelType.LLM,
                size_gb=4.0,
                min_vram_gb=4.0,
                min_ram_gb=8.0,
                recommended_vram_gb=6.0,
                recommended_ram_gb=12.0,
                supports_quantization=True,
                huggingface_id="small/model",
            ),
            ModelMetadata(
                name="Large",
                provider=ModelProvider.LLAMA,
                model_type=ModelType.LLM,
                size_gb=10.0,
                min_vram_gb=12.0,
                min_ram_gb=12.0,
                recommended_vram_gb=16.0,
                recommended_ram_gb=20.0,
                supports_quantization=True,
                huggingface_id="large/model",
            ),
        ]


class _SwapRegistry:
    def get_model(self, model_id: str):
        del model_id
        return None


def test_canvas_memory_tracker_estimates_history_memory() -> None:
    scene = _Scene(
        undo_history=[
            {
                "type": "image",
                "before": {
                    "image": _airaw_bytes(64, 64),
                    "image_width": 64,
                    "image_height": 64,
                },
                "after": {"mask": _airaw_bytes(64, 64)},
            }
        ],
        redo_history=[],
    )

    vram_gb, ram_gb = CanvasMemoryTracker().estimate_history_memory(scene)

    assert vram_gb > 0.0
    assert ram_gb > 0.0


def test_quantization_strategy_selects_expected_level() -> None:
    config = QuantizationStrategy().select_quantization(
        model_size_gb=8.0,
        hardware=_hardware_profile(available_vram_gb=16.0),
    )

    assert config.level is QuantizationLevel.FLOAT16


def test_memory_allocator_tracks_allocations() -> None:
    allocator = MemoryAllocator(_hardware_profile(available_vram_gb=16.0))
    quantization = QuantizationConfig(
        level=QuantizationLevel.INT8,
        description="8-bit quantization",
        estimated_memory_gb=6.0,
    )

    allocation = allocator.allocate("test-model", quantization)

    assert allocation is not None
    assert allocator.get_total_allocated_vram() == 6.0

    allocator.deallocate("test-model")

    assert allocator.get_total_allocated_vram() == 0.0


def test_model_registry_keeps_static_whisper_metadata() -> None:
    registry = ModelRegistry()

    metadata = registry.get_model("ggml-large-v3.bin")

    assert metadata is not None
    assert metadata.model_type is ModelType.SPEECH_TO_TEXT
    assert metadata.runtime_backend == "whisper.cpp"


def test_model_state_mixin_tracks_active_models() -> None:
    manager = _DummyResourceManager()
    quantization = QuantizationConfig(
        level=QuantizationLevel.INT8,
        description="8-bit quantization",
        estimated_memory_gb=6.0,
    )

    manager.memory_allocator.allocate("model-a", quantization)
    manager.model_loaded("model-a", model_type="llm")

    active_models = manager.get_active_models()

    assert len(active_models) == 1
    assert active_models[0].model_id == "model-a"
    assert active_models[0].state is ModelState.LOADED


def test_memory_tracking_mixin_reports_breakdown() -> None:
    manager = _DummyResourceManager()

    manager.update_canvas_history_allocation(vram_gb=1.0, ram_gb=0.5)
    manager.update_external_apps_allocation(vram_gb=2.0)
    breakdown = manager.get_memory_allocation_breakdown()

    assert breakdown.canvas_history_vram_gb == 1.0
    assert breakdown.canvas_history_ram_gb == 0.5
    assert breakdown.external_apps_vram_gb == 2.0


def test_model_selection_mixin_prefers_largest_feasible_model() -> None:
    manager = _DummyResourceManager()

    selected = manager.select_best_model(ModelProvider.LLAMA, ModelType.LLM)

    assert selected is not None
    assert selected.name == "Large"


def test_model_loading_mixin_requests_unload_through_hook() -> None:
    loader = _SwapLoader()
    quantization = QuantizationConfig(
        level=QuantizationLevel.INT8,
        description="8-bit quantization",
        estimated_memory_gb=6.0,
    )

    loader.memory_allocator.allocate("loaded-model", quantization)
    loader.model_loaded("loaded-model", model_type="tts")
    result = loader.request_model_swap("next-model", "llm")

    assert result["success"] is True
    assert result["unloaded_models"] == ["loaded-model"]
    assert loader.unloaded == [("loaded-model", "tts")]


def test_model_resource_manager_uses_injected_unload_callback() -> None:
    hardware = _hardware_profile(available_vram_gb=16.0)
    allocator = MemoryAllocator(hardware)
    quantization = QuantizationConfig(
        level=QuantizationLevel.INT8,
        description="8-bit quantization",
        estimated_memory_gb=6.0,
    )
    unloaded: list[tuple[str, str]] = []
    manager = _PureModelResourceManager(
        logger=_Logger(),
        unload_model_callback=lambda model_id, model_type: unloaded.append(
            (model_id, model_type)
        ),
        hardware_profiler=_Profiler(hardware),
        quantization_strategy=QuantizationStrategy(),
        registry=_SwapRegistry(),
        memory_allocator=allocator,
        canvas_memory_tracker=CanvasMemoryTracker(),
    )

    allocator.allocate("loaded-model", quantization)
    manager.model_loaded("loaded-model", model_type="tts")
    result = manager.request_model_swap("next-model", "llm")

    assert result["success"] is True
    assert result["unloaded_models"] == ["loaded-model"]
    assert unloaded == [("loaded-model", "tts")]