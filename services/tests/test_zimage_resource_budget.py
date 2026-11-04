"""Resource guards for the exact pretrained Z-Image loading path."""

from __future__ import annotations

import json
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from airunner_services.art.managers.zimage.mixins.zimage_pretrained_loader_helper import (
    ZImagePretrainedLoaderHelper,
)
from airunner_services.art.managers.zimage.mixins import (
    zimage_pretrained_loader_helper as loader_module,
)
from airunner_services.art.managers.zimage.zimage_resource_budget import (
    ComponentMemoryEstimate,
    ZImageMemoryPlan,
    build_zimage_memory_plan,
    estimate_quantized_component,
)
from airunner_services.art.managers.zimage import zimage_resource_budget as budget_module
from airunner_services.model_management._base_model_resource_manager import (
    ModelResourceManager as BaseModelResourceManager,
)
from airunner_services.model_management.hardware_profiler import HardwareProfile
from airunner_services.model_management.memory_allocator import (
    MemoryAllocation,
    MemoryAllocator,
)
from airunner_services.model_management.model_registry import ModelRegistry
from airunner_services.model_management.quantization_strategy import (
    QuantizationConfig,
    QuantizationLevel,
)
from airunner_services.model_management.types import ModelState


_DTYPE_BYTES = {"BF16": 2, "F32": 4}


@pytest.fixture
def isolated_resource_manager():
    previous = BaseModelResourceManager._instance
    BaseModelResourceManager._instance = None
    try:
        yield
    finally:
        BaseModelResourceManager._instance = previous


def _write_shard(
    path: Path,
    tensors: dict[str, tuple[str, list[int]]],
) -> dict[str, object]:
    """Write a valid sparse safetensors shard for header-only tests."""
    offset = 0
    header: dict[str, object] = {}
    for name, (dtype, shape) in tensors.items():
        size = _DTYPE_BYTES[dtype]
        for dim in shape:
            size *= dim
        header[name] = {
            "dtype": dtype,
            "shape": shape,
            "data_offsets": [offset, offset + size],
        }
        offset += size
    encoded = json.dumps(header, separators=(",", ":")).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        stream.write(struct.pack("<Q", len(encoded)))
        stream.write(encoded)
        stream.truncate(stream.tell() + offset)
    return header


def _component(
    root: Path,
    directory_name: str,
    *,
    tensor: tuple[str, str, list[int]],
) -> None:
    component = root / directory_name
    name, dtype, shape = tensor
    shard_name = "weights.safetensors"
    _write_shard(component / shard_name, {name: (dtype, shape)})
    index_name = (
        "diffusion_pytorch_model.safetensors.index.json"
        if directory_name in {"transformer", "vae"}
        else "model.safetensors.index.json"
    )
    (component / index_name).write_text(
        json.dumps({"weight_map": {name: shard_name}}),
        encoding="utf-8",
    )


def _small_model(root: Path) -> None:
    _component(
        root,
        "transformer",
        tensor=("blocks.0.proj.weight", "F32", [100, 100]),
    )
    _component(
        root,
        "text_encoder",
        tensor=("model.embed_tokens.weight", "BF16", [100, 100]),
    )
    _component(root, "vae", tensor=("decoder.weight", "BF16", [100, 100]))


def test_estimate_quantized_component_uses_header_and_keeps_embeddings(
    tmp_path: Path,
) -> None:
    component = tmp_path / "transformer"
    _write_shard(
        component / "weights.safetensors",
        {
            "blocks.0.proj.weight": ("F32", [100, 100]),
            "model.embed_tokens.weight": ("BF16", [10, 10]),
            "norm.weight": ("BF16", [10]),
        },
    )
    (component / "diffusion_pytorch_model.safetensors.index.json").write_text(
        json.dumps(
            {
                "weight_map": {
                    "blocks.0.proj.weight": "weights.safetensors",
                    "model.embed_tokens.weight": "weights.safetensors",
                    "norm.weight": "weights.safetensors",
                }
            }
        ),
        encoding="utf-8",
    )

    estimate = estimate_quantized_component(component)

    assert estimate.source_tensor_bytes == 40_220
    assert estimate.estimated_resident_bytes == 7_720
    assert estimate.tensor_count == 3
    estimate_8bit = estimate_quantized_component(
        component,
        quantization_bits=8,
    )
    estimate_unquantized = estimate_quantized_component(
        component,
        quantization_bits=None,
    )
    assert estimate_8bit.estimated_resident_bytes == 15_220
    assert estimate_unquantized.estimated_resident_bytes == 40_220
    estimate_float32 = estimate_quantized_component(
        component,
        target_dtype_bytes=4,
    )
    assert estimate_float32.estimated_resident_bytes == 7_940


def test_vae_header_rejects_out_of_bounds_tensor_offsets(tmp_path: Path) -> None:
    component = tmp_path / "vae"
    shard = component / "weights.safetensors"
    header = json.dumps(
        {
            "decoder.weight": {
                "dtype": "BF16",
                "shape": [2, 2],
                "data_offsets": [0, 4],
            }
        }
    ).encode()
    shard.parent.mkdir(parents=True)
    shard.write_bytes(struct.pack("<Q", len(header)) + header + bytes(8))

    with pytest.raises(ValueError, match="byte-size mismatch"):
        budget_module.estimate_unquantized_component(component)


def test_component_residency_uses_selected_float_dtype(tmp_path: Path) -> None:
    transformer = tmp_path / "transformer"
    text_encoder = tmp_path / "text_encoder"
    vae = tmp_path / "vae"
    _component(
        tmp_path,
        "transformer",
        tensor=("blocks.0.proj.bias", "F32", [4]),
    )
    _component(
        tmp_path,
        "text_encoder",
        tensor=("model.norm.weight", "BF16", [4]),
    )
    _component(
        tmp_path,
        "vae",
        tensor=("decoder.bias", "F32", [4]),
    )

    transformer_bf16 = estimate_quantized_component(
        transformer,
        quantization_bits=None,
        target_dtype_bytes=2,
    )
    text_encoder_float32 = estimate_quantized_component(
        text_encoder,
        quantization_bits=None,
        target_dtype_bytes=4,
    )
    vae_bf16 = budget_module.estimate_unquantized_component(
        vae,
        target_dtype_bytes=2,
    )

    assert transformer_bf16.source_tensor_bytes == 16
    assert transformer_bf16.estimated_resident_bytes == 8
    assert text_encoder_float32.source_tensor_bytes == 8
    assert text_encoder_float32.estimated_resident_bytes == 16
    assert vae_bf16.source_tensor_bytes == 16
    assert vae_bf16.estimated_resident_bytes == 8


def test_vae_bfloat16_residency_expands_for_float32_target(tmp_path: Path) -> None:
    _component(
        tmp_path,
        "vae",
        tensor=("decoder.bias", "BF16", [4]),
    )

    estimate = budget_module.estimate_unquantized_component(
        tmp_path / "vae",
        target_dtype_bytes=4,
    )

    assert estimate.source_tensor_bytes == 8
    assert estimate.estimated_resident_bytes == 16


def test_safetensors_index_read_is_size_capped(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    component = tmp_path / "vae"
    _component(
        tmp_path,
        "vae",
        tensor=("decoder.weight", "BF16", [2, 2]),
    )
    index = component / "diffusion_pytorch_model.safetensors.index.json"
    monkeypatch.setattr(budget_module, "_MAX_INDEX_BYTES", 8)

    with pytest.raises(ValueError, match="exceeds size limit"):
        budget_module.estimate_unquantized_component(component)


def test_resource_plan_fails_when_live_vram_cannot_support_four_bit(
    tmp_path: Path,
) -> None:
    _small_model(tmp_path)

    with pytest.raises(RuntimeError, match="at least 4.00 GiB"):
        build_zimage_memory_plan(
            tmp_path,
            available_vram_gib=8.0,
            available_ram_gib=32.0,
            reserved_vram_gib=1.5,
            reserved_ram_gib=2.0,
        )


def test_preflight_accepts_ordinary_pretrained_directory_without_receipts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _small_model(tmp_path)
    profile = HardwareProfile(
        total_vram_gb=16.0,
        available_vram_gb=12.0,
        total_ram_gb=32.0,
        available_ram_gb=16.0,
        cuda_available=True,
        cuda_compute_capability=(12, 0),
        device_name="test GPU",
        cpu_count=8,
        platform="linux",
    )

    class FakeProfiler:
        def get_profile(self) -> HardwareProfile:
            return profile

    manager = SimpleNamespace(
        hardware_profiler=FakeProfiler(),
        memory_allocator=SimpleNamespace(
            _reserved_vram_gb=1.5,
            _reserved_ram_gb=2.0,
        ),
    )
    monkeypatch.setattr(loader_module, "ModelResourceManager", lambda: manager)
    helper = ZImagePretrainedLoaderHelper(
        SimpleNamespace(logger=Mock(), data_type=object())
    )

    plan = helper.build_memory_plan(
        tmp_path,
        use_quantization=True,
        quantization_bits=4,
    )

    assert plan.quantization_bits == 4
    assert plan.transformer.tensor_count == 1
    assert not (tmp_path / "manifest.json").exists()
    assert not (tmp_path / "intake-validation.json").exists()


def test_resource_plan_fails_when_host_ram_is_below_required_reserve(
    tmp_path: Path,
) -> None:
    _small_model(tmp_path)

    with pytest.raises(RuntimeError, match="available after reserves"):
        build_zimage_memory_plan(
            tmp_path,
            available_vram_gib=16.0,
            available_ram_gib=5.5,
            reserved_vram_gib=1.5,
            reserved_ram_gib=2.0,
        )


def test_unquantized_plan_accounts_for_cpu_residency(tmp_path: Path) -> None:
    _small_model(tmp_path)
    plan = build_zimage_memory_plan(
        tmp_path,
        available_vram_gib=0.0,
        available_ram_gib=32.0,
        reserved_vram_gib=1.5,
        reserved_ram_gib=2.0,
        quantization_bits=None,
    )

    assert plan.quantization_bits is None
    assert plan.gpu_weight_budget_gib == 0.0
    assert plan.cpu_weight_budget_gib > 0.0


def test_unquantized_plan_uses_cuda_only_when_the_full_pipeline_fits(
    tmp_path: Path,
) -> None:
    _small_model(tmp_path)
    cpu_plan = build_zimage_memory_plan(
        tmp_path,
        available_vram_gib=4.5,
        available_ram_gib=32.0,
        reserved_vram_gib=1.5,
        reserved_ram_gib=2.0,
        quantization_bits=None,
    )
    gpu_plan = build_zimage_memory_plan(
        tmp_path,
        available_vram_gib=16.0,
        available_ram_gib=32.0,
        reserved_vram_gib=1.5,
        reserved_ram_gib=2.0,
        quantization_bits=None,
    )

    assert cpu_plan.gpu_weight_budget_gib == 0.0
    assert cpu_plan.gpu_activation_reserve_gib == 3.0
    assert gpu_plan.gpu_weight_budget_gib > 0.0
    assert gpu_plan.cpu_weight_budget_gib == pytest.approx(
        gpu_plan.transformer.estimated_resident_gib
        + gpu_plan.text_encoder.estimated_resident_gib
        + gpu_plan.vae.estimated_resident_gib
    )


def test_eight_bit_mode_is_preserved_in_resource_plan(tmp_path: Path) -> None:
    _small_model(tmp_path)
    plan = build_zimage_memory_plan(
        tmp_path,
        available_vram_gib=16.0,
        available_ram_gib=32.0,
        reserved_vram_gib=1.5,
        reserved_ram_gib=2.0,
        quantization_bits=8,
    )

    assert plan.quantization_bits == 8
    assert plan.gpu_activation_reserve_gib == 3.0


def test_activation_headroom_is_part_of_the_coordinator_reservation() -> None:
    plan = _plan()
    assert plan.estimated_vram_gib == pytest.approx(5.25)
    profile = HardwareProfile(
        total_vram_gb=16.0,
        available_vram_gb=7.5,
        total_ram_gb=32.0,
        available_ram_gb=16.0,
        cuda_available=True,
        cuda_compute_capability=(12, 0),
        device_name="test GPU",
        cpu_count=8,
        platform="linux",
    )
    allocator = MemoryAllocator(profile)
    first = allocator.allocate(
        "zimage",
        QuantizationConfig(
            level=QuantizationLevel.INT4,
            description="budgeted ART model",
            estimated_memory_gb=plan.estimated_vram_gib,
            estimated_ram_gb=4.0,
        ),
    )
    second = allocator.allocate(
        "other-load",
        QuantizationConfig(
            level=QuantizationLevel.INT4,
            description="competing allocation",
            estimated_memory_gb=1.0,
            estimated_ram_gb=4.0,
        ),
    )

    assert first is not None
    assert first.vram_allocated_gb == pytest.approx(5.25)
    assert second is None


def test_concurrent_allocations_cannot_both_admit_against_same_capacity() -> None:
    profile = HardwareProfile(
        total_vram_gb=16.0,
        available_vram_gb=8.0,
        total_ram_gb=32.0,
        available_ram_gb=16.0,
        cuda_available=True,
        cuda_compute_capability=(12, 0),
        device_name="test GPU",
        cpu_count=8,
        platform="linux",
    )

    class SlowAdmissionAllocator(MemoryAllocator):
        def can_allocate(self, model_id, quantization):
            result = super().can_allocate(model_id, quantization)
            time.sleep(0.05)
            return result

    allocator = SlowAdmissionAllocator(profile)
    start = threading.Barrier(3)
    request = QuantizationConfig(
        level=QuantizationLevel.INT4,
        description="concurrent test allocation",
        estimated_memory_gb=4.0,
        estimated_ram_gb=4.0,
    )

    def allocate(model_id: str):
        start.wait(timeout=2)
        return allocator.allocate(model_id, request)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(allocate, "first")
        second = executor.submit(allocate, "second")
        start.wait(timeout=2)
        results = (first.result(timeout=3), second.result(timeout=3))

    assert sum(result is not None for result in results) == 1
    assert len(allocator._allocations) == 1


def _plan() -> ZImageMemoryPlan:
    component = ComponentMemoryEstimate(
        estimated_resident_bytes=1024**3,
        source_tensor_bytes=2 * 1024**3,
        largest_shard_bytes=512 * 1024**2,
        tensor_count=1,
    )
    vae = ComponentMemoryEstimate(
        estimated_resident_bytes=256 * 1024**2,
        source_tensor_bytes=256 * 1024**2,
        largest_shard_bytes=256 * 1024**2,
        tensor_count=1,
    )
    return ZImageMemoryPlan(
        transformer=component,
        text_encoder=component,
        vae=vae,
        gpu_weight_budget_gib=2.25,
        cpu_weight_budget_gib=0.0,
        cpu_workspace_gib=0.75,
        transformer_gpu_gib=1.0,
        transformer_cpu_gib=0.0,
        text_encoder_gpu_gib=1.0,
        text_encoder_cpu_gib=0.0,
        vae_gpu_gib=0.25,
        vae_cpu_gib=0.0,
        gpu_activation_reserve_gib=3.0,
        quantization_bits=4,
        max_memory_transformer={0: "1.00GiB", "cpu": "0.00GiB"},
        max_memory_text_encoder={0: "1.00GiB", "cpu": "0.00GiB"},
    )


def test_pretrained_loader_rechecks_capacity_before_text_encoder(
    tmp_path: Path,
) -> None:
    owner = SimpleNamespace(
        model_path=str(tmp_path),
        logger=Mock(),
    )
    helper = ZImagePretrainedLoaderHelper(owner)
    helper.load_transformer_from_pretrained = Mock(return_value=object())
    helper.load_text_encoder_from_pretrained = Mock(return_value=(object(), object()))
    helper.load_vae_from_pretrained = Mock(return_value=object())
    helper._check_live_capacity = Mock(
        side_effect=RuntimeError("live capacity changed")
    )

    with pytest.raises(RuntimeError, match="live capacity changed"):
        helper._load_components(
            tmp_path,
            transformer_cfg=None,
            text_encoder_cfg=None,
            model_dtype=None,
            plan=_plan(),
            use_quant=True,
            quant_bits=4,
        )

    helper.load_transformer_from_pretrained.assert_called_once()
    helper.load_text_encoder_from_pretrained.assert_not_called()
    helper.load_vae_from_pretrained.assert_not_called()


def test_live_capacity_recheck_accounts_for_other_inflight_loads(
    isolated_resource_manager,
) -> None:
    profile = HardwareProfile(
        total_vram_gb=16.0,
        available_vram_gb=12.0,
        total_ram_gb=32.0,
        available_ram_gb=16.0,
        cuda_available=True,
        cuda_compute_capability=(12, 0),
        device_name="test GPU",
        cpu_count=8,
        platform="linux",
    )

    class FakeProfiler:
        def get_profile(self) -> HardwareProfile:
            return profile

    manager = BaseModelResourceManager(
        hardware_profiler=FakeProfiler(),  # type: ignore[arg-type]
        registry=ModelRegistry(),
        memory_allocator=MemoryAllocator(profile),
    )
    manager.set_model_state("other-art", ModelState.LOADING, "text_to_image")
    manager.memory_allocator._allocations["other-art"] = MemoryAllocation(
        model_id="other-art",
        vram_allocated_gb=5.0,
        ram_allocated_gb=5.0,
        device="cuda:0",
    )

    allowed, reason, _ = manager.check_live_load_capacity(
        "zimage",
        required_vram_gb=6.0,
        required_ram_gb=4.0,
    )

    assert not allowed
    assert "Insufficient live VRAM" in reason


def test_art_preflight_does_not_accept_an_unregistered_model(
    isolated_resource_manager,
) -> None:
    profile = HardwareProfile(
        total_vram_gb=16.0,
        available_vram_gb=12.0,
        total_ram_gb=32.0,
        available_ram_gb=16.0,
        cuda_available=True,
        cuda_compute_capability=(12, 0),
        device_name="test GPU",
        cpu_count=8,
        platform="linux",
    )

    class FakeProfiler:
        def get_profile(self) -> HardwareProfile:
            return profile

    manager = BaseModelResourceManager(
        hardware_profiler=FakeProfiler(),  # type: ignore[arg-type]
        registry=ModelRegistry(),
        memory_allocator=MemoryAllocator(profile),
    )

    result = manager.prepare_model_loading(
        "unregistered-art-path",
        model_type="text_to_image",
        require_registered=True,
    )

    assert not result["can_load"]
    assert "not registered" in result["reason"]
