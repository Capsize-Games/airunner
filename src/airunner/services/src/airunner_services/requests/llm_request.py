"""Compatibility wrapper for the service-owned LLM request model."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.llm.llm_request")
sys.modules[__name__] = _module