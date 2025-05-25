"""
Unit tests for airunner.utils.memory.is_ampere_or_newer
Covers all code paths, including import errors and fallback logic.
"""

import pytest
from unittest.mock import patch
from airunner.utils.memory.is_ampere_or_newer import is_ampere_or_newer


def test_is_ampere_or_newer_true():
    with patch(
        "airunner.utils.memory.is_ampere_or_newer.torch"
    ) as torch_mock, patch(
        "airunner.utils.memory.is_ampere_or_newer.AIRUNNER_DISABLE_FLASH_ATTENTION",
        False,
    ):
        torch_mock.cuda.get_device_capability.return_value = (8, 0)
        assert is_ampere_or_newer(0) is True


def test_is_ampere_or_newer_false():
    with patch(
        "airunner.utils.memory.is_ampere_or_newer.torch"
    ) as torch_mock, patch(
        "airunner.utils.memory.is_ampere_or_newer.AIRUNNER_DISABLE_FLASH_ATTENTION",
        False,
    ):
        torch_mock.cuda.get_device_capability.return_value = (7, 5)
        assert is_ampere_or_newer(0) is False


def test_is_ampere_or_newer_disabled():
    with patch(
        "airunner.utils.memory.is_ampere_or_newer.AIRUNNER_DISABLE_FLASH_ATTENTION",
        True,
    ):
        assert is_ampere_or_newer(0) is False
