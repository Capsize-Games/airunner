"""Compatibility wrapper for `airunner_model.contracts`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_model.contracts")
sys.modules[__name__] = _module