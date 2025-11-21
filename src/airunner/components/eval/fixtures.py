"""
Pytest fixtures for AI Runner evaluation testing.

Provides fixtures to connect to the running airunner-headless systemd service
for testing. Tests should NOT start their own server - they use the existing
service on port 8080.

Usage:
    def test_llm_generation(airunner_client):
        response = airunner_client.generate("What is 2+2?")
        assert "4" in response["text"]
"""

import time

import pytest
import requests

from airunner.components.eval.client import AIRunnerClient
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.settings import (
    AIRUNNER_HEADLESS_SERVER_HOST,
    AIRUNNER_HEADLESS_SERVER_PORT,
)

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _wait_for_server_health(base_url: str, timeout: int = 10) -> bool:
    """Poll server health endpoint until ready or timeout."""
    start_time = time.time()
    logger.info(f"Checking if server at {base_url}/health is ready...")

    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{base_url}/health", timeout=1)
            if response.status_code == 200:
                logger.info("Server is ready!")
                return True
        except requests.RequestException as e:
            logger.debug(f"Health check failed: {e}")
        time.sleep(0.5)

    return False


@pytest.fixture(scope="session")
def airunner_server():
    """Verify the airunner-headless systemd service is running.

    This fixture does NOT start a server - it checks that the existing
    systemd service on port 8080 is accessible.

    Raises:
        RuntimeError: If server is not accessible
    """
    base_url = f"http://{AIRUNNER_HEADLESS_SERVER_HOST}:{AIRUNNER_HEADLESS_SERVER_PORT}"

    logger.info(
        f"Checking for running airunner-headless service on port {AIRUNNER_HEADLESS_SERVER_PORT}..."
    )

    if not _wait_for_server_health(base_url, timeout=10):
        raise RuntimeError(
            f"airunner-headless service is not running on port {AIRUNNER_HEADLESS_SERVER_PORT}. "
            f"Start it with: sudo systemctl start airunner-headless"
        )

    logger.info("✓ Found running airunner-headless service")
    yield base_url
    # No cleanup - we don't own the server


@pytest.fixture(scope="session")
def airunner_client(airunner_server: str) -> AIRunnerClient:
    """Create AIRunnerClient instance connected to systemd service.

    Args:
        airunner_server: The base URL of the running service

    Returns:
        AIRunnerClient: Configured client instance
    """
    client = AIRunnerClient(base_url=airunner_server)

    # Verify client can connect
    try:
        client.health_check()
    except Exception as e:
        pytest.fail(f"Failed to connect to server: {e}")

    return client


@pytest.fixture
def airunner_client_function_scope(airunner_server: str) -> AIRunnerClient:
    """Create function-scoped AIRunnerClient instance.

    Use this fixture when you need a fresh client for each test function.

    Args:
        airunner_server: The base URL of the running service

    Returns:
        AIRunnerClient: New client instance
    """
    client = AIRunnerClient(base_url=airunner_server)
    # Ensure fresh conversation for each test function to avoid duplication
    try:
        client.reset_memory()
    except Exception:
        # Not fatal - continue even if reset fails
        logger.exception("Failed to reset memory for test client")
    return client
