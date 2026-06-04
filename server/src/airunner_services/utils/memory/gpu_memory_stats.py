"""Service-owned helpers for reading GPU memory statistics."""

from __future__ import annotations

from typing import Dict

import torch


def _fallback_used_free(
    total_gb: float,
    reserved_gb: float,
) -> tuple[float, float]:
    """Return used/free estimates when driver stats are unavailable."""
    used_gb = min(max(reserved_gb, 0.0), total_gb)
    free_gb = max(total_gb - used_gb, 0.0)
    return used_gb, free_gb


def _driver_used_free(
    device: torch.device,
    total_gb: float,
) -> tuple[float, float]:
    """Return device-wide used/free memory in gigabytes."""
    reserved_gb = torch.cuda.memory_reserved(device) / (1024**3)
    try:
        free_bytes, total_bytes = torch.cuda.mem_get_info(device)
    except RuntimeError:
        return _fallback_used_free(total_gb, reserved_gb)

    total_gb = total_bytes / (1024**3)
    free_gb = free_bytes / (1024**3)
    used_gb = max(total_gb - free_gb, 0.0)
    return used_gb, free_gb


def gpu_memory_stats(device: torch.device) -> Dict[str, float | str]:
    """Return GPU memory statistics for one torch device."""
    stats: Dict[str, float | str] = {
        "total": 0.0,
        "used": 0.0,
        "allocated": 0.0,
        "reserved": 0.0,
        "free": 0.0,
        "device_name": "N/A",
    }
    if device.type != "cuda":
        return stats

    total_gb = (
        torch.cuda.get_device_properties(device).total_memory / (1024**3)
    )
    reserved_gb = torch.cuda.memory_reserved(device) / (1024**3)
    used_gb, free_gb = _driver_used_free(device, total_gb)
    stats.update(
        {
            "total": total_gb,
            "used": used_gb,
            "allocated": torch.cuda.memory_allocated(device) / (1024**3),
            "reserved": reserved_gb,
            "free": free_gb,
            "device_name": torch.cuda.get_device_name(device),
        }
    )
    return stats


__all__ = ["gpu_memory_stats"]
