"""Compatibility wrapper for the service-owned art module."""

from importlib import import_module as _import_module
import sys

_module = _import_module(
    "airunner_services.model_management.zimage_model_manager"
)
sys.modules[__name__] = _module
