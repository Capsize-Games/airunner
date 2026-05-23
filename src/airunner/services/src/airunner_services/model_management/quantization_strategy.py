"""Compatibility wrapper for `airunner_model.model_management.quantization_strategy`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_model.model_management.quantization_strategy")
sys.modules[__name__] = _module