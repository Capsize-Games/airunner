"""Transitional API wrapper for one daemon runtime status response model."""

from importlib import import_module as _import_module
import sys

_module = _import_module(
    "airunner_services.api.models.daemon_runtime_status_response"
)
sys.modules[__name__] = _module