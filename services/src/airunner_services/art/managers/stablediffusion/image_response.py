"""Compatibility wrapper for the service-owned image response type."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.requests.image_response")
sys.modules[__name__] = _module
