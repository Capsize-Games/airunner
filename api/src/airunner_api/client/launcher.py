"""API-owned import surface for the local daemon launcher."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.daemon_client.launcher")
sys.modules[__name__] = _module