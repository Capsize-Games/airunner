"""Compatibility wrapper for the service-owned web tools module."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.tools.web_tools")
sys.modules[__name__] = _module
