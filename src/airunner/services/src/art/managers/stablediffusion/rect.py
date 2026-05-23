"""Compatibility wrapper for the service-owned Rect helper."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.requests.rect")
sys.modules[__name__] = _module
