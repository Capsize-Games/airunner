"""Compatibility wrapper for the service-owned language detector."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.utils.text.language_detection")
sys.modules[__name__] = _module
