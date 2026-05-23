"""Compatibility wrapper for `airunner_model.runtimes.tts_daemon_runtime_settings`."""

from importlib import import_module as _import_module
import sys

_module = _import_module(
    "airunner_model.runtimes.tts_daemon_runtime_settings"
)
sys.modules[__name__] = _module