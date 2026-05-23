"""Compatibility wrapper for `airunner_model.runtimes.bundled_runtime_paths`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_model.runtimes.bundled_runtime_paths")
sys.modules[__name__] = _module