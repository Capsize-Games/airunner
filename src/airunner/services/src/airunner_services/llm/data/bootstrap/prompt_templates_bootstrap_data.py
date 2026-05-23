"""Compatibility wrapper for the service-owned prompt template seeds."""

from importlib import import_module as _import_module
import sys

_module = _import_module(
    "airunner_services.bootstrap.prompt_templates_bootstrap_data"
)
sys.modules[__name__] = _module
