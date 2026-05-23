"""Compatibility wrapper for the service-owned stream-text helpers."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.llm.stream_text")
sys.modules[__name__] = _module