"""Transitional API wrapper for `airunner_services.api.api_service_base`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.api.api_service_base")
sys.modules[__name__] = _module