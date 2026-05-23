"""Compatibility wrapper for the service-owned LLM generate worker."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.workers.llm_generate_worker")
sys.modules[__name__] = _module
