"""
Unit tests for random_seed in random_seed.py.
Covers normal and edge cases.
"""

import pytest
from unittest.mock import patch


def test_random_seed_normal():
    with patch(
        "airunner.utils.application.random_seed._random_generator.randint",
        return_value=42,
    ):
        from airunner.utils.application.random_seed import random_seed

        assert random_seed() == 42


def test_random_seed_max_seed():
    import importlib

    rs_mod = importlib.import_module("airunner.utils.application.random_seed")
    old_max_seed = getattr(rs_mod, "AIRUNNER_MAX_SEED", None)
    rs_mod.AIRUNNER_MAX_SEED = 0
    try:
        result = rs_mod.random_seed()
        assert result == 0
    finally:
        if old_max_seed is not None:
            rs_mod.AIRUNNER_MAX_SEED = old_max_seed
        else:
            delattr(rs_mod, "AIRUNNER_MAX_SEED")
