"""Focused mixins used by the top-level App class."""

from airunner.app_mixins.localization_mixin import LocalizationMixin
from airunner.app_mixins.ui_runtime_mixin import UIRuntimeMixin

__all__ = [
    "LocalizationMixin",
    "UIRuntimeMixin",
]