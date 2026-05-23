"""Compatibility wrapper for service-owned provider access policy helpers."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.downloads.policy")
sys.modules[__name__] = _module