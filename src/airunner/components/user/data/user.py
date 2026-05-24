"""Compatibility re-export for the User model.

This model was consolidated into ``airunner_model.models.user``.
This module is kept as a backward-compatible shim.
"""

from airunner_model.models.user import User

__all__ = ["User"]
