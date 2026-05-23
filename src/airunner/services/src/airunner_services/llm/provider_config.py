"""Compatibility wrapper for the model-owned provider config."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_model.llm.provider_config")
sys.modules[__name__] = _module