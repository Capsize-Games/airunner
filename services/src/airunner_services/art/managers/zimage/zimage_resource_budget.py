"""Conservative, header-only memory estimates for pretrained Z-Image."""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_DTYPE_BYTES = {
    "BOOL": 1,
    "U8": 1,
    "I8": 1,
    "F8_E4M3": 1,
    "F8_E4M3FN": 1,
    "F8_E5M2": 1,
    "F8_E5M2FNUZ": 1,
    "U16": 2,
    "I16": 2,
    "F16": 2,
    "BF16": 2,
    "U32": 4,
    "I32": 4,
    "F32": 4,
    "U64": 8,
    "I64": 8,
    "F64": 8,
}
_GIB = 1024**3
_QUANTIZED_WEIGHT_BYTES_PER_VALUE = {4: 0.75, 8: 1.5}
_LOAD_WORKSPACE_FACTOR = 1.25
_MAX_HEADER_BYTES = 128 * 1024 * 1024
_MAX_INDEX_BYTES = 64 * 1024 * 1024
_MIN_SUPPORTED_GPU_GIB = 4.0


def _read_weight_map(component_dir: Path) -> dict[str, str] | None:
    """Read a bounded Hugging Face safetensors index when one is present."""
    for name in (
        "model.safetensors.index.json",
        "diffusion_pytorch_model.safetensors.index.json",
    ):
        index_path = component_dir / name
        if not index_path.is_file():
            continue
        size = index_path.stat().st_size
        if size <= 0 or size > _MAX_INDEX_BYTES:
            raise ValueError(f"Safetensors index exceeds size limit: {index_path}")
        with index_path.open("rb") as stream:
            encoded = stream.read(_MAX_INDEX_BYTES + 1)
        if len(encoded) > _MAX_INDEX_BYTES:
            raise ValueError(f"Safetensors index exceeds size limit: {index_path}")
        index = json.loads(encoded)
        weight_map = index.get("weight_map") if isinstance(index, dict) else None
        if not isinstance(weight_map, dict) or not weight_map:
            raise ValueError(f"Invalid safetensors index: {index_path}")
        if any(
            not isinstance(tensor_name, str)
            or not isinstance(shard_name, str)
            or not shard_name
            for tensor_name, shard_name in weight_map.items()
        ):
            raise ValueError(f"Invalid safetensors index entries: {index_path}")
        return weight_map
    return None


def _read_validated_safetensors_header(
    shard: Path,
) -> list[tuple[str, str, list[int], int]]:
    """Parse and validate a bounded safetensors header and payload layout."""
    shard_size = shard.stat().st_size
    with shard.open("rb") as stream:
        prefix = stream.read(8)
        if len(prefix) != 8:
            raise ValueError(f"Invalid safetensors header: {shard}")
        header_size = struct.unpack("<Q", prefix)[0]
        if header_size <= 0 or header_size > _MAX_HEADER_BYTES:
            raise ValueError(f"Invalid safetensors header size: {shard}")
        encoded = stream.read(header_size)
        if len(encoded) != header_size:
            raise ValueError(f"Truncated safetensors header: {shard}")
    header = json.loads(encoded)
    if not isinstance(header, dict):
        raise ValueError(f"Invalid safetensors header object: {shard}")
    payload_bytes = shard_size - 8 - header_size
    tensors: list[tuple[str, str, list[int], int, int]] = []
    for name, spec in header.items():
        if name == "__metadata__":
            continue
        if not isinstance(name, str) or not isinstance(spec, dict):
            raise ValueError(f"Invalid tensor header entry: {shard}:{name}")
        dtype = spec.get("dtype")
        shape = spec.get("shape")
        offsets = spec.get("data_offsets")
        if (
            dtype not in _DTYPE_BYTES
            or not isinstance(shape, list)
            or not all(
                isinstance(dim, int) and not isinstance(dim, bool) and dim >= 0
                for dim in shape
            )
            or not isinstance(offsets, list)
            or len(offsets) != 2
            or not all(
                isinstance(value, int) and not isinstance(value, bool)
                for value in offsets
            )
        ):
            raise ValueError(f"Invalid tensor header: {shard}:{name}")
        tensor_bytes = math.prod(shape) * _DTYPE_BYTES[dtype]
        start, end = offsets
        if (
            start < 0
            or end < start
            or end > payload_bytes
            or end - start != tensor_bytes
        ):
            raise ValueError(f"Tensor byte-size mismatch: {shard}:{name}")
        tensors.append((name, dtype, shape, start, end))

    cursor = 0
    for _, _, _, start, end in sorted(tensors, key=lambda item: item[3]):
        if start != cursor:
            raise ValueError(f"Invalid safetensors payload layout: {shard}")
        cursor = end
    if cursor != payload_bytes:
        raise ValueError(f"Invalid safetensors payload size: {shard}")
    return [(name, dtype, shape, end - start) for name, dtype, shape, start, end in tensors]


@dataclass(frozen=True)
class ComponentMemoryEstimate:
    """Estimated component residency and largest source-shard workspace."""

    estimated_resident_bytes: int
    source_tensor_bytes: int
    largest_shard_bytes: int
    tensor_count: int

    @property
    def estimated_resident_gib(self) -> float:
        return self.estimated_resident_bytes / _GIB

    @property
    def largest_shard_workspace_gib(self) -> float:
        return math.ceil(
            self.largest_shard_bytes * _LOAD_WORKSPACE_FACTOR
        ) / _GIB


@dataclass(frozen=True)
class ZImageMemoryPlan:
    """One shared estimate for transformer, encoder, VAE and load workspace.

    These values are conservative estimates derived from safetensors headers
    and shard sizes. They are not measured runtime peaks.
    """

    transformer: ComponentMemoryEstimate
    text_encoder: ComponentMemoryEstimate
    vae: ComponentMemoryEstimate
    gpu_weight_budget_gib: float
    cpu_weight_budget_gib: float
    cpu_workspace_gib: float
    transformer_gpu_gib: float
    transformer_cpu_gib: float
    text_encoder_gpu_gib: float
    text_encoder_cpu_gib: float
    vae_gpu_gib: float
    vae_cpu_gib: float
    gpu_activation_reserve_gib: float
    quantization_bits: int | None
    max_memory_transformer: dict[Any, str]
    max_memory_text_encoder: dict[Any, str]

    @property
    def estimated_vram_gib(self) -> float:
        # Keep activation memory in the coordinator reservation too. Otherwise
        # another in-flight allocation could consume headroom that the staged
        # component checks assume remains free.
        return self.gpu_weight_budget_gib + self.gpu_activation_reserve_gib

    @property
    def estimated_ram_gib(self) -> float:
        return max(4.0, self.cpu_weight_budget_gib + self.cpu_workspace_gib)


def estimate_quantized_component(
    component_dir: Path,
    *,
    quantization_bits: int | None = 4,
    target_dtype_bytes: int | None = None,
) -> ComponentMemoryEstimate:
    """Estimate a component from local safetensors headers only.

    Rank-two ``*.weight`` tensors are treated as quantizable linear weights,
    except embeddings, output heads and normalization tensors. Other tensors
    retain their source storage size. Four/eight-bit estimates include 50%
    overhead over packed parameter storage. No tensor payload is decoded.
    """
    if quantization_bits not in (None, 4, 8):
        raise ValueError(f"Unsupported Z-Image quantization: {quantization_bits}")
    quantization_factor = (
        _QUANTIZED_WEIGHT_BYTES_PER_VALUE.get(quantization_bits)
        if quantization_bits is not None
        else None
    )
    weight_map = _read_weight_map(component_dir)
    if weight_map is None:
        raise ValueError(f"Missing safetensors index in {component_dir}")

    root = component_dir.resolve()
    shard_names = sorted(set(weight_map.values()))
    if len(shard_names) > 4096:
        raise ValueError(f"Too many safetensors shards in {component_dir}")
    source_bytes = 0
    estimated_bytes = 0
    largest_shard = 0
    tensor_count = 0
    for shard_name in shard_names:
        shard = (component_dir / shard_name).resolve()
        if root not in shard.parents or not shard.is_file():
            raise ValueError(f"Invalid or missing safetensors shard: {shard_name}")
        shard_size = shard.stat().st_size
        largest_shard = max(largest_shard, shard_size)
        tensors = _read_validated_safetensors_header(shard)
        expected_names = {
            name
            for name, mapped_shard in weight_map.items()
            if mapped_shard == shard_name
        }
        if {name for name, _, _, _ in tensors} != expected_names:
            raise ValueError(f"Safetensors index/header mismatch: {shard}")
        for name, dtype, shape, tensor_bytes in tensors:
            source_bytes += tensor_bytes
            tensor_count += 1
            lower_name = name.lower()
            quantizable = (
                name.endswith(".weight")
                and len(shape) == 2
                and not any(
                    token in lower_name
                    for token in ("embed", "lm_head", "norm", "shared")
                )
            )
            if quantizable and quantization_factor is not None:
                estimated_bytes += math.ceil(
                    math.prod(shape) * quantization_factor
                )
            else:
                target_bytes = _DTYPE_BYTES[dtype]
                if dtype.startswith(("F", "BF")) and target_dtype_bytes:
                    target_bytes = target_dtype_bytes
                estimated_bytes += math.prod(shape) * target_bytes

    return ComponentMemoryEstimate(
        estimated_resident_bytes=estimated_bytes,
        source_tensor_bytes=source_bytes,
        largest_shard_bytes=largest_shard,
        tensor_count=tensor_count,
    )


def estimate_unquantized_component(
    component_dir: Path,
    *,
    target_dtype_bytes: int | None = None,
) -> ComponentMemoryEstimate:
    """Estimate VAE residency from one or more local safetensors files."""
    weight_map = _read_weight_map(component_dir)
    shard_names = (
        sorted(set(weight_map.values()))
        if weight_map is not None
        else sorted(path.name for path in component_dir.glob("*.safetensors"))
    )
    if len(shard_names) > 4096:
        raise ValueError(f"Too many safetensors shards in {component_dir}")
    root = component_dir.resolve()
    candidates = []
    for shard_name in shard_names:
        shard = (component_dir / shard_name).resolve()
        if root not in shard.parents or not shard.is_file():
            raise ValueError(f"Invalid or missing safetensors shard: {shard_name}")
        candidates.append(shard)
    if not candidates:
        raise ValueError(f"Missing VAE safetensors in {component_dir}")
    total = 0
    source_total = 0
    largest = 0
    count = 0
    for shard in candidates:
        largest = max(largest, shard.stat().st_size)
        tensors = _read_validated_safetensors_header(shard)
        if weight_map is not None:
            expected_names = {
                name
                for name, mapped_shard in weight_map.items()
                if mapped_shard == shard.name
            }
            if {name for name, _, _, _ in tensors} != expected_names:
                raise ValueError(f"Safetensors index/header mismatch: {shard}")
        for _, dtype, shape, tensor_bytes in tensors:
            source_total += tensor_bytes
            tensor_bytes = _DTYPE_BYTES[dtype]
            if dtype.startswith(("F", "BF")) and target_dtype_bytes:
                tensor_bytes = target_dtype_bytes
            total += math.prod(shape) * tensor_bytes
            count += 1
    return ComponentMemoryEstimate(
        estimated_resident_bytes=total,
        source_tensor_bytes=source_total,
        largest_shard_bytes=largest,
        tensor_count=count,
    )


def build_zimage_memory_plan(
    model_dir: Path,
    *,
    available_vram_gib: float,
    available_ram_gib: float,
    reserved_vram_gib: float,
    reserved_ram_gib: float,
    quantization_bits: int | None = 4,
    activation_reserve_gib: float = 3.0,
    target_dtype_bytes: int | None = None,
) -> ZImageMemoryPlan:
    """Build one component budget from fresh available-memory readings."""
    transformer = estimate_quantized_component(
        model_dir / "transformer",
        quantization_bits=quantization_bits,
        target_dtype_bytes=target_dtype_bytes,
    )
    text_encoder = estimate_quantized_component(
        model_dir / "text_encoder",
        quantization_bits=quantization_bits,
        target_dtype_bytes=target_dtype_bytes,
    )
    vae = estimate_unquantized_component(
        model_dir / "vae",
        target_dtype_bytes=target_dtype_bytes,
    )
    uses_device_map = quantization_bits is not None
    gpu_capacity = max(0.0, available_vram_gib - reserved_vram_gib - activation_reserve_gib)
    cpu_capacity = max(0.0, available_ram_gib - reserved_ram_gib)
    if uses_device_map and gpu_capacity < _MIN_SUPPORTED_GPU_GIB:
        raise RuntimeError(
            f"Z-Image {quantization_bits}-bit resource preflight failed: at least "
            f"{_MIN_SUPPORTED_GPU_GIB:.2f} GiB of model VRAM is required "
            f"after GPU and activation reserves; available is "
            f"{gpu_capacity:.2f} GiB"
        )
    total_weights = (
        transformer.estimated_resident_gib
        + text_encoder.estimated_resident_gib
        + vae.estimated_resident_gib
    )
    if uses_device_map:
        gpu_weights = min(total_weights, gpu_capacity)
    else:
        # The runtime moves the whole unquantized pipeline to CUDA when it
        # fits; otherwise it enables model CPU offload.
        gpu_weights = total_weights if total_weights <= gpu_capacity else 0.0
    # The nonquantized pretrained loaders stage components in RAM before the
    # later pipeline placement step, even when all weights ultimately fit GPU.
    cpu_weights = total_weights if not uses_device_map else total_weights - gpu_weights
    cpu_workspace = max(
        transformer.largest_shard_workspace_gib,
        text_encoder.largest_shard_workspace_gib,
        vae.largest_shard_workspace_gib,
    )
    cpu_required = max(4.0, cpu_weights + cpu_workspace)
    if cpu_required > cpu_capacity:
        raise RuntimeError(
        f"Z-Image {quantization_bits or 'unquantized'} resource preflight failed: estimated component "
            f"weights need {gpu_weights:.2f} GiB GPU and "
            f"{cpu_required:.2f} GiB RAM including the "
            f"largest-shard workspace; available after reserves is "
            f"{gpu_capacity:.2f} GiB GPU and {cpu_capacity:.2f} GiB RAM"
        )

    # Reserve VAE residency first because quantized Z-Image moves it to CUDA.
    vae_gpu = min(vae.estimated_resident_gib, gpu_weights)
    remaining_gpu = max(0.0, gpu_weights - vae_gpu)
    transformer_gpu = min(transformer.estimated_resident_gib, remaining_gpu)
    transformer_cpu = (
        transformer.estimated_resident_gib
        if not uses_device_map
        else max(0.0, transformer.estimated_resident_gib - transformer_gpu)
    )
    text_encoder_gpu = min(
        text_encoder.estimated_resident_gib,
        max(0.0, remaining_gpu - transformer_gpu),
    )
    text_encoder_cpu = (
        text_encoder.estimated_resident_gib
        if not uses_device_map
        else max(0.0, text_encoder.estimated_resident_gib - text_encoder_gpu)
    )
    vae_cpu = (
        vae.estimated_resident_gib
        if not uses_device_map
        else max(0.0, vae.estimated_resident_gib - vae_gpu)
    )
    transformer_max = {0: f"{transformer_gpu:.2f}GiB"}
    text_encoder_max = {0: f"{text_encoder_gpu:.2f}GiB"}
    if transformer_cpu > 0.0:
        transformer_max["cpu"] = f"{transformer_cpu:.2f}GiB"
    if text_encoder_cpu > 0.0:
        text_encoder_max["cpu"] = f"{text_encoder_cpu:.2f}GiB"
    return ZImageMemoryPlan(
        transformer=transformer,
        text_encoder=text_encoder,
        vae=vae,
        gpu_weight_budget_gib=gpu_weights,
        cpu_weight_budget_gib=cpu_weights,
        cpu_workspace_gib=cpu_workspace,
        transformer_gpu_gib=transformer_gpu,
        transformer_cpu_gib=transformer_cpu,
        text_encoder_gpu_gib=text_encoder_gpu,
        text_encoder_cpu_gib=text_encoder_cpu,
        vae_gpu_gib=vae_gpu,
        vae_cpu_gib=vae_cpu,
        gpu_activation_reserve_gib=activation_reserve_gib,
        quantization_bits=quantization_bits,
        max_memory_transformer=transformer_max,
        max_memory_text_encoder=text_encoder_max,
    )
