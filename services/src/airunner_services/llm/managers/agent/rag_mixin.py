"""Compatibility wrapper for the service-owned RAG mixin."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.llm.rag_mixin")
sys.modules[__name__] = _module