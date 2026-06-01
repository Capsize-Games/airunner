"""Client-side VRAM calculation utilities.

Pure functions — no filesystem access, no torch.  Model file size and
native dtype are queried from the daemon via
``GET /api/v1/art/vram-estimate``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

# Display names for precision options
PRECISION_DISPLAY_NAMES: Dict[str, str] = {
    "4bit": "4-bit (Lowest VRAM)",
    "8bit": "8-bit",
    "float8": "FP8",
    "bfloat16": "BF16",
    "float16": "FP16",
    "float32": "FP32 (Highest Quality)",
}

# Bytes per parameter for each dtype
BYTES_PER_PARAM: Dict[str, float] = {
    "float32": 4.0,
    "float16": 2.0,
    "bfloat16": 2.0,
    "float8": 1.0,
    "8bit": 1.2,
    "4bit": 0.6,
}

VRAM_OVERHEAD_GB = 4.0


@dataclass
class VRAMEstimate:
    """Container for VRAM usage estimate."""

    model_vram_gb: float
    overhead_gb: float
    total_vram_gb: float
    precision: str


def estimate_vram_for_precision(
    model_size_gb: float,
    target_precision: str,
    source_precision: str = "bfloat16",
) -> VRAMEstimate:
    source_bytes = BYTES_PER_PARAM.get(source_precision, 2.0)
    target_bytes = BYTES_PER_PARAM.get(target_precision, 2.0)
    scale_factor = target_bytes / source_bytes
    model_vram_gb = model_size_gb * scale_factor
    overhead_gb = VRAM_OVERHEAD_GB
    total_vram_gb = model_vram_gb + overhead_gb
    return VRAMEstimate(
        model_vram_gb=round(model_vram_gb, 1),
        overhead_gb=overhead_gb,
        total_vram_gb=round(total_vram_gb, 1),
        precision=target_precision,
    )


def can_use_precision(
    target_precision: str,
    native_precision: str,
) -> bool:
    precision_order = [
        "float32",
        "bfloat16",
        "float16",
        "float8",
        "8bit",
        "4bit",
    ]
    try:
        native_idx = precision_order.index(native_precision)
        target_idx = precision_order.index(target_precision)
    except ValueError:
        return True
    return target_idx >= native_idx


def get_available_precisions(
    native_precision: str,
) -> list[str]:
    all_precisions = [
        "float32",
        "bfloat16",
        "float16",
        "float8",
        "8bit",
        "4bit",
    ]
    return [
        p for p in all_precisions
        if can_use_precision(p, native_precision)
    ]


def is_precision_safe_for_vram(
    estimate: VRAMEstimate,
    available_vram_gb: float,
) -> bool:
    safety_margin = 2.0
    required_vram = estimate.total_vram_gb + safety_margin
    return available_vram_gb >= required_vram
