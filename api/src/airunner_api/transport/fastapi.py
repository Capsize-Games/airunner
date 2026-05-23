"""API-owned import surface for the FastAPI transport adapter."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.api.server")
sys.modules[__name__] = _module