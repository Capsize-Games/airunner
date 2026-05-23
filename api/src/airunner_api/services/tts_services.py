"""API-owned import surface for the TTS service facade."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.api.services.tts_services")
sys.modules[__name__] = _module