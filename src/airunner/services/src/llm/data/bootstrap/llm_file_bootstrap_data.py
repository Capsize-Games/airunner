"""Compatibility wrapper for `airunner_services.bootstrap.llm_file_bootstrap_data`."""

from importlib import import_module as _import_module
import sys


_module = _import_module("airunner_services.bootstrap.llm_file_bootstrap_data")
sys.modules[__name__] = _module
