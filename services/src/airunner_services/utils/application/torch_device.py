"""Service-owned torch-device helper."""

from __future__ import annotations

import torch

from airunner_services.utils.application.get_logger import get_logger

logger = get_logger(__name__)


def get_torch_device(card_index: int = 0):
    """Return the preferred torch device for one card index."""
    use_cuda = torch.cuda.is_available()
    if not use_cuda:
        logger.warning("CUDA NOT AVAILABLE, USING CPU")
    return torch.device(f"cuda:{card_index}" if use_cuda else "cpu")


__all__ = ["get_torch_device"]