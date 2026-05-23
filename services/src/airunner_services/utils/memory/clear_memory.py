"""Service-owned helpers for clearing accelerator memory."""

from __future__ import annotations

import gc
from typing import Any

try:
    import torch
except ImportError:  # pragma: no cover - optional dependency
    torch = None


def _resolve_cuda_device(device: Any) -> int | None:
    """Normalize supported CUDA device selectors."""
    if device is None:
        return 0
    if isinstance(device, int):
        return device
    if torch is not None and isinstance(device, torch.device):
        if device.type != "cuda":
            return None
        return 0 if device.index is None else int(device.index)
    if isinstance(device, str):
        value = device.strip().lower()
        if not value or value.startswith("cpu"):
            return None
        if value.isdigit():
            return int(value)
        if value.startswith("cuda"):
            _, _, suffix = value.partition(":")
            return int(suffix) if suffix.isdigit() else 0
    return 0


def clear_memory(device=0) -> None:
    """Clear one CUDA cache when applicable and collect garbage."""
    cuda_device = _resolve_cuda_device(device)
    if (
        torch is not None
        and hasattr(torch, "cuda")
        and cuda_device is not None
        and torch.cuda.is_available()
    ):
        try:
            torch.cuda.set_device(cuda_device)
            torch.cuda.empty_cache()
            if hasattr(torch.cuda, "reset_max_memory_allocated"):
                torch.cuda.reset_max_memory_allocated(device=cuda_device)
            if hasattr(torch.cuda, "reset_max_memory_cached"):
                torch.cuda.reset_max_memory_cached(device=cuda_device)
            torch.cuda.synchronize(device=cuda_device)
        except RuntimeError:
            print("Failed to clear memory")
    gc.collect()


__all__ = ["clear_memory"]
