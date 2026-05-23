"""Compatibility wrapper for the service-owned LLM model manager."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.model_management.llm_model_manager")
sys.modules[__name__] = _module
