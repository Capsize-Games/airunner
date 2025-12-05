"""VRAM estimation utilities for model loading.

This module provides utilities for estimating VRAM usage based on model size
and precision settings, helping users choose appropriate precision options
for their hardware.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Tuple
import os


# Multipliers for VRAM usage relative to FP32
# These represent how much VRAM a model uses at each precision compared to FP32
PRECISION_VRAM_MULTIPLIERS: Dict[str, float] = {
    "float32": 1.0,        # 32 bits = 4 bytes per param
    "float16": 0.5,        # 16 bits = 2 bytes per param
    "bfloat16": 0.5,       # 16 bits = 2 bytes per param
    "float8": 0.25,        # 8 bits = 1 byte per param
    "8bit": 0.28,          # ~8 bits + some overhead for BitsAndBytes
    "4bit": 0.15,          # ~4 bits + overhead for NF4 quantization
}

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
    "8bit": 1.2,  # ~8 bits + overhead (linear8bit has some overhead)
    "4bit": 0.6,  # ~4 bits + overhead (NF4 has some overhead)
}

# Overhead estimate for pipeline activations, caches, etc.
# This is a rough estimate and varies by model architecture
# VAE decode can temporarily spike VRAM by ~2-3GB for large images
# KV cache during text encoding also adds ~1-2GB
VRAM_OVERHEAD_GB = 4.0


def get_vram_safety_margin_gb() -> float:
    """Get VRAM safety margin needed for generation.
    
    This accounts for:
    - VAE decode memory spike (~1-2GB for 1024x1024)
    - CUDA memory fragmentation
    - OS/driver overhead
    
    Returns:
        Safety margin in GB.
    """
    return 2.0


def is_precision_safe_for_vram(
    estimate: "VRAMEstimate",
    available_vram_gb: float,
) -> bool:
    """Check if a precision setting is safe for the available VRAM.
    
    Args:
        estimate: VRAMEstimate for the precision.
        available_vram_gb: Total VRAM available in GB.
        
    Returns:
        True if the precision is likely safe to use.
    """
    safety_margin = get_vram_safety_margin_gb()
    required_vram = estimate.total_vram_gb + safety_margin
    return available_vram_gb >= required_vram


def get_recommended_precision_for_vram(
    model_size_gb: float,
    available_vram_gb: float,
    source_precision: str = "bfloat16",
) -> str:
    """Get the recommended precision for a given VRAM size.
    
    Recommends the highest quality precision that fits safely in VRAM.
    
    Args:
        model_size_gb: Model size in GB.
        available_vram_gb: Available VRAM in GB.
        source_precision: The precision the model is stored in.
        
    Returns:
        Recommended precision string (e.g., "4bit", "8bit", "bfloat16").
    """
    # Try precisions from highest quality to lowest
    precision_order = ["bfloat16", "float16", "8bit", "4bit"]
    
    for precision in precision_order:
        estimate = estimate_vram_for_precision(model_size_gb, precision, source_precision)
        if is_precision_safe_for_vram(estimate, available_vram_gb):
            return precision
    
    # Default to 4-bit if nothing else fits
    return "4bit"


@dataclass
class VRAMEstimate:
    """Container for VRAM usage estimate."""

    model_vram_gb: float
    overhead_gb: float
    total_vram_gb: float
    precision: str
    
    def __str__(self) -> str:
        """Return human-readable VRAM estimate string."""
        return f"~{self.total_vram_gb:.1f} GB"


def get_model_file_size_gb(model_path: str) -> Optional[float]:
    """Get the total size of model files in gigabytes.
    
    Handles both single .safetensors files and directories with multiple files.
    
    Args:
        model_path: Path to the model file or directory.
        
    Returns:
        Total size in GB, or None if path doesn't exist.
    """
    path = Path(model_path)
    
    if not path.exists():
        return None
    
    total_bytes = 0
    
    if path.is_file():
        total_bytes = path.stat().st_size
    elif path.is_dir():
        # Sum all safetensors, bin, and pt files
        for pattern in ("*.safetensors", "*.bin", "*.pt", "**/*.safetensors", "**/*.bin"):
            for file in path.glob(pattern):
                if file.is_file():
                    total_bytes += file.stat().st_size
    
    return total_bytes / (1024 ** 3)


def estimate_vram_for_precision(
    model_size_gb: float,
    target_precision: str,
    source_precision: str = "bfloat16",
) -> VRAMEstimate:
    """Estimate VRAM usage for a model at a given precision.
    
    This function estimates VRAM usage by scaling the model size based on
    the precision conversion ratio.
    
    Args:
        model_size_gb: Size of the model files in GB (at source_precision).
        target_precision: The precision to estimate VRAM for.
        source_precision: The precision the model is stored in (default: bfloat16).
        
    Returns:
        VRAMEstimate with model VRAM, overhead, and total.
    """
    # Get bytes per param for source and target
    source_bytes = BYTES_PER_PARAM.get(source_precision, 2.0)  # Default to fp16
    target_bytes = BYTES_PER_PARAM.get(target_precision, 2.0)
    
    # Scale model size based on precision change
    scale_factor = target_bytes / source_bytes
    model_vram_gb = model_size_gb * scale_factor
    
    # Add overhead for activations, caches, etc.
    # Note: Overhead is relatively constant regardless of precision
    overhead_gb = VRAM_OVERHEAD_GB
    
    total_vram_gb = model_vram_gb + overhead_gb
    
    return VRAMEstimate(
        model_vram_gb=round(model_vram_gb, 1),
        overhead_gb=overhead_gb,
        total_vram_gb=round(total_vram_gb, 1),
        precision=target_precision,
    )


def estimate_vram_from_path(
    model_path: str,
    target_precision: str,
    source_precision: str = "bfloat16",
) -> Optional[VRAMEstimate]:
    """Estimate VRAM usage for a model at a given precision.
    
    Args:
        model_path: Path to the model file or directory.
        target_precision: The precision to estimate VRAM for.
        source_precision: The precision the model is stored in.
        
    Returns:
        VRAMEstimate or None if model path doesn't exist.
    """
    model_size_gb = get_model_file_size_gb(model_path)
    if model_size_gb is None:
        return None
    
    return estimate_vram_for_precision(
        model_size_gb=model_size_gb,
        target_precision=target_precision,
        source_precision=source_precision,
    )


def format_vram_estimate(estimate: VRAMEstimate) -> str:
    """Format VRAM estimate for display in UI.
    
    Args:
        estimate: The VRAM estimate to format.
        
    Returns:
        Formatted string like "~11.5 GB VRAM"
    """
    return f"~{estimate.total_vram_gb:.1f} GB VRAM"


def get_precision_with_vram_estimate(
    precision: str,
    model_path: Optional[str] = None,
    model_size_gb: Optional[float] = None,
    source_precision: str = "bfloat16",
) -> Tuple[str, Optional[VRAMEstimate]]:
    """Get display name for precision option with VRAM estimate.
    
    Args:
        precision: The precision value (e.g., "bfloat16", "4bit").
        model_path: Optional path to model for size calculation.
        model_size_gb: Optional pre-calculated model size in GB.
        source_precision: The precision the model is stored in.
        
    Returns:
        Tuple of (display_name, VRAMEstimate or None).
    """
    display_name = PRECISION_DISPLAY_NAMES.get(precision, precision)
    
    estimate = None
    if model_path:
        estimate = estimate_vram_from_path(
            model_path, precision, source_precision
        )
    elif model_size_gb is not None:
        estimate = estimate_vram_for_precision(
            model_size_gb, precision, source_precision
        )
    
    return display_name, estimate


def can_use_precision(
    target_precision: str,
    native_precision: str,
) -> bool:
    """Check if a precision option is valid for a model.
    
    Models can be loaded at their native precision or LOWER precisions,
    but not at HIGHER precisions (can't add information that isn't there).
    
    For example:
    - A fp16 model can be loaded at fp16, 8bit, or 4bit
    - A fp16 model should NOT be loaded at fp32 (would waste memory)
    - A bf16 model can be loaded at bf16, fp16, 8bit, or 4bit
    
    Args:
        target_precision: The precision the user wants to use.
        native_precision: The precision the model is stored in.
        
    Returns:
        True if the precision option is valid.
    """
    # Precision hierarchy from highest to lowest
    # Higher index = lower precision (less memory)
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
        # Unknown precision - allow it
        return True
    
    # Allow target precision if it's at same level or lower (higher index)
    return target_idx >= native_idx


def get_available_precisions(
    native_precision: str,
) -> list[str]:
    """Get list of valid precision options for a model.
    
    Args:
        native_precision: The precision the model is stored in.
        
    Returns:
        List of valid precision values.
    """
    all_precisions = ["float32", "bfloat16", "float16", "float8", "8bit", "4bit"]
    return [p for p in all_precisions if can_use_precision(p, native_precision)]
