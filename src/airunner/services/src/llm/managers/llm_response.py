"""Compatibility wrapper for the service-owned LLM response model."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.llm.llm_response")
sys.modules[__name__] = _module
