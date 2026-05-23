"""Transitional API wrapper for `airunner_services.bin.airunner_headless`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.bin.airunner_headless")
sys.modules[__name__] = _module