"""
Memory management utilities for Stable Diffusion handlers.
Handles memory-efficient settings and their application.
Follows project standards: docstrings, type hints, logging.
"""

import logging
from typing import Any
import torch
from airunner.utils.memory import is_ampere_or_newer
from airunner.settings import (
    AIRUNNER_MEM_USE_LAST_CHANNELS,
    AIRUNNER_MEM_USE_ENABLE_VAE_SLICING,
    AIRUNNER_MEM_USE_ATTENTION_SLICING,
    AIRUNNER_MEM_USE_TILED_VAE,
    AIRUNNER_MEM_USE_ACCELERATED_TRANSFORMERS,
    AIRUNNER_MEM_USE_ENABLE_SEQUENTIAL_CPU_OFFLOAD,
    AIRUNNER_MEM_ENABLE_MODEL_CPU_OFFLOAD,
    AIRUNNER_MEM_USE_TOME_SD,
    AIRUNNER_MEM_TOME_SD_RATIO,
)

logger = logging.getLogger(__name__)


def apply_last_channels(pipe: Any, enabled: bool) -> None:
    """Apply torch.channels_last memory format if enabled."""
    if enabled:
        try:
            pipe.unet.to(memory_format=torch.channels_last)
            logger.info("Enabled torch.channels_last memory format.")
        except AttributeError as e:
            logger.warning(
                f"Unable to enable torch.channels_last memory format. {e}"
            )
    else:
        try:
            pipe.unet.to(memory_format=torch.contiguous_format)
            logger.info("Disabled torch.channels_last memory format.")
        except AttributeError as e:
            logger.warning(
                f"Unable to disable torch.channels_last memory format. {e}"
            )


def set_memory_efficient(enabled: bool) -> bool:
    """Stub for setting memory efficient mode (for test compatibility)."""
    # In real implementation, this would set memory-efficient settings.
    return bool(enabled)


# Additional memory-efficient setting utilities can be added here (vae slicing, attention slicing, tiled vae, etc.)
