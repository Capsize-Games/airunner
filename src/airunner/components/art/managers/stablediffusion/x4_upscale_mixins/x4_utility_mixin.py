"""
Utility mixin for X4UpscaleManager.

This mixin provides helper utilities for cache management and
out-of-memory detection.
"""

import torch


class X4UtilityMixin:
    """Utility methods for X4UpscaleManager."""

    def _empty_cache(self):
        """Clear CUDA cache if available.

        Calls torch.cuda.empty_cache() to free up GPU memory between
        operations. Safe to call even if CUDA is not available.
        """
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass

    @staticmethod
    def _is_out_of_memory(exc: Exception) -> bool:
        """Check if exception indicates out-of-memory error.

        Args:
            exc: Exception to check.

        Returns:
            True if exception is CUDA OOM error or message contains
            'out of memory'.
        """
        message = str(exc).lower()
        return "out of memory" in message or isinstance(
            exc, torch.cuda.OutOfMemoryError
        )
