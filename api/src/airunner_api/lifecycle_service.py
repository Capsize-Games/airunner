"""Transitional API wrapper for `airunner_services.lifecycle_service`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.lifecycle_service")
sys.modules[__name__] = _module