"""Compatibility wrapper for service-owned TTS text preprocessing."""

from importlib import import_module as _import_module
import sys

_module = _import_module(
    "airunner_services.utils.text.tts_preprocessing"
)
sys.modules[__name__] = _module
