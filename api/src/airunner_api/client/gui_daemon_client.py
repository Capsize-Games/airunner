"""API-owned import surface for the local daemon client."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.daemon_client.gui_daemon_client")
sys.modules[__name__] = _module