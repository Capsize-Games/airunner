"""
Unit tests for melo.models
"""

import pytest
import importlib

models = importlib.import_module("airunner.vendor.melo.models")


def test_models_module_importable():
    assert models is not None
