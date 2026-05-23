"""Compatibility wrapper for the service-owned LLM settings."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.llm.llm_settings")
sys.modules[__name__] = _module