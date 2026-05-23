"""Compatibility wrapper for `airunner_api.messages`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_api.messages")
sys.modules[__name__] = _module