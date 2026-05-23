"""API-owned import surface for the STT service facade."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.api.services.stt_services")
sys.modules[__name__] = _module