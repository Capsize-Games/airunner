"""Transitional API wrapper for `airunner_services.api.routes.legacy`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.api.routes.legacy")
sys.modules[__name__] = _module