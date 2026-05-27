"""Compatibility re-export for the User model.

This model was consolidated into ``airunner.models.user``.
This module is kept as a backward-compatible shim.
"""

from airunner.models.user import User

__all__ = ["User"]
