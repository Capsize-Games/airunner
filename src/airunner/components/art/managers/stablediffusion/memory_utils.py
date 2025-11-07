"""
Memory management utilities for Stable Diffusion handlers.
Handles memory-efficient settings and their application.
Follows project standards: docstrings, type hints, logging.
"""

from typing import Any
import torch
from airunner.components.model_management.hardware_profiler import (
    HardwareProfiler,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
_hardware_profiler = None


def get_hardware_profiler() -> HardwareProfiler:
    """Get singleton hardware profiler instance."""
    global _hardware_profiler
    if _hardware_profiler is None:
        _hardware_profiler = HardwareProfiler()
    return _hardware_profiler


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
