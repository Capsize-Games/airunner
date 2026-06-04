"""Runtime memory helpers for service-owned art manager code."""

from __future__ import annotations

import torch

from airunner_services.utils.memory.clear_memory import clear_memory as _clear


def clear_memory(device=0) -> None:
    """Clear cached device memory using the shared service helper."""
    _clear(device=device)


def is_ampere_or_newer(device: int) -> bool:
    """Return whether the selected CUDA device is Ampere or newer."""
    if not torch.cuda.is_available():
        return False

    try:
        major, _minor = torch.cuda.get_device_capability(device)
    except Exception:
        return False

    return major >= 8


__all__ = ["clear_memory", "is_ampere_or_newer"]