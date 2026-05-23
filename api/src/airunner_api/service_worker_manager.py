"""Transitional API wrapper for `airunner_services.service_worker_manager`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.service_worker_manager")
sys.modules[__name__] = _module