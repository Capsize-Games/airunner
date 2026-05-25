"""Transitional API wrapper for `airunner_services.setup_database`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.setup_database")
sys.modules[__name__] = _module