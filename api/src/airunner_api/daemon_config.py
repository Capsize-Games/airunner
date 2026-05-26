"""Transitional API wrapper for `airunner_model.runtimes.daemon_config`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_model.runtimes.daemon_config")
sys.modules[__name__] = _module