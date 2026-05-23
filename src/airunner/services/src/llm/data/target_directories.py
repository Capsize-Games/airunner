"""Compatibility wrapper for the service-owned target-directory model."""

from importlib import import_module as _import_module
import sys

_module = _import_module(
    "airunner_services.database.models.target_directories"
)
sys.modules[__name__] = _module
