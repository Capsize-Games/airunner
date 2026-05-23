"""Compatibility wrapper for the service-owned tool manager."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.llm.tool_manager")
sys.modules[__name__] = _module