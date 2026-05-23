"""Compatibility wrapper for `airunner_model.runtimes.sidecar_stt_launcher`."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_model.runtimes.sidecar_stt_launcher")
sys.modules[__name__] = _module