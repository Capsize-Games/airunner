"""
Unit tests for melo.utils
"""

import pytest
import importlib

utils = importlib.import_module("airunner.vendor.melo.utils")


def test_utils_module_importable():
    assert utils is not None
