"""Transitional API wrapper for `airunner_services.utils.db.bootstrap`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.utils.db.bootstrap")
sys.modules[__name__] = _module