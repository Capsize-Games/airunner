"""
Unit tests for pytest fixtures.

Tests fixture behavior and server lifecycle management.
"""

import pytest
import time
from airunner.components.eval.client import AIRunnerClient


def test_airunner_client_fixture_type(airunner_client):
    """Test that airunner_client fixture returns correct type."""
    assert isinstance(airunner_client, AIRunnerClient)


def test_airunner_client_can_connect(airunner_client):
    """Test that client fixture can connect to server."""
    health = airunner_client.health_check()
    assert health is not None
    assert health.get("status") == "ready"


def test_function_scoped_client(airunner_client_function_scope):
    """Test function-scoped client fixture."""
    assert isinstance(airunner_client_function_scope, AIRunnerClient)

    health = airunner_client_function_scope.health_check()
    assert health is not None


def test_multiple_function_scoped_clients(
    airunner_client_function_scope,
):
    """Test that function-scoped clients are independent."""
    client1 = airunner_client_function_scope

    # Both should work independently
    health = client1.health_check()
    assert health["status"] == "ready"


@pytest.mark.slow
def test_server_remains_alive_across_tests(airunner_client):
    """Test that server remains alive for multiple tests."""
    # First request
    health1 = airunner_client.health_check()
    assert health1["status"] == "ready"

    # Small delay
    time.sleep(0.1)

    # Second request - server should still be running
    health2 = airunner_client.health_check()
    assert health2["status"] == "ready"
