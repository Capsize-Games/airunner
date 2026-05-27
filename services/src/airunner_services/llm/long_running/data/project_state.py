"""Compatibility wrapper for the service-owned project state module."""

from importlib import import_module as _import_module
import sys

_module = _import_module("airunner_services.database.models.project_state")
sys.modules[__name__] = _module
