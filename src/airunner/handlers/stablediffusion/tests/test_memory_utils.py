"""
Unit tests for memory_utils.py utility functions in stablediffusion handler.
Covers memory-efficient settings logic.
"""

import pytest
import airunner.handlers.stablediffusion.memory_utils as memory_utils


def test_set_memory_efficient_true():
    # Should set memory efficient mode
    result = memory_utils.set_memory_efficient(True)
    assert result is True


def test_set_memory_efficient_false():
    # Should unset memory efficient mode
    result = memory_utils.set_memory_efficient(False)
    assert result is False
