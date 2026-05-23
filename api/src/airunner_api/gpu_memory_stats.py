"""Transitional API wrapper for `airunner_services.utils.memory.gpu_memory_stats`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.utils.memory.gpu_memory_stats")
sys.modules[__name__] = _module