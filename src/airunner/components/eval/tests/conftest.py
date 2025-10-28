"""Pytest configuration for eval tests."""

# Import fixtures to make them available to all test files
from airunner.components.eval.fixtures import (
    airunner_server,
    airunner_client,
    airunner_client_function_scope,
)

__all__ = [
    "airunner_server",
    "airunner_client",
    "airunner_client_function_scope",
]
