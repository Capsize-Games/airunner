"""Transitional API wrapper for `airunner_services.utils.db.column`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.utils.db.column")
sys.modules[__name__] = _module