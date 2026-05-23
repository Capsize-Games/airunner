"""Transitional API wrapper for `airunner_services.api.routes.llm`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.api.routes.llm")
sys.modules[__name__] = _module