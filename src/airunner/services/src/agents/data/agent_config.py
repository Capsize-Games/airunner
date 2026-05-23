"""Compatibility wrapper for the service-owned agent config model."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.database.models.agent_config")
sys.modules[__name__] = _module
