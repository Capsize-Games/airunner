"""Transitional API wrapper for `airunner_services.app.headless_runtime_mixin`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.app.headless_runtime_mixin")
sys.modules[__name__] = _module