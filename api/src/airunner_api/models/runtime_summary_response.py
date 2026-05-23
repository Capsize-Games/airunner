"""Transitional API wrapper for one runtime summary response model."""

from importlib import import_module as _import_module
import sys

_module = _import_module(
    "airunner_services.api.models.runtime_summary_response"
)
sys.modules[__name__] = _module