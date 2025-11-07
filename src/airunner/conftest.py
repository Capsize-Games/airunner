"""
Root conftest for AI Runner tests.

This file configures pytest for the entire test suite.
"""

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "trio: mark test to run with trio async backend"
    )


@pytest.fixture(scope="session")
def anyio_backend():
    """
    Override the default anyio_backend fixture to only use asyncio.

    This prevents tests from being parametrized with trio, which is not
    installed and not needed for AI Runner.
    """
    return "asyncio"
