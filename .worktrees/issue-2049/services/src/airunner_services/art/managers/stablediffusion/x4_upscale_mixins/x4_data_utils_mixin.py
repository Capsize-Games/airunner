"""
Small data utilities for X4 upscaler.

Contains helpers used by data preparation to keep functions short.
"""

from typing import Dict


class X4DataUtilsMixin:
    def _normalize_request_fields(self, **kwargs) -> Dict:
        """Placeholder normalization hook for request building."""
        return kwargs
