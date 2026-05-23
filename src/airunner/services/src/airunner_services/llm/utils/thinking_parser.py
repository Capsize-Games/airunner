"""Compatibility wrapper for the service-owned thinking parser."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.llm.thinking_parser")
sys.modules[__name__] = _module
