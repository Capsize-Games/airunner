"""Compatibility wrapper for the service-owned image request type."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.requests.image_request")
sys.modules[__name__] = _module
