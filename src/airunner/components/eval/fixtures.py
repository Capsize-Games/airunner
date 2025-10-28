"""
Pytest fixtures for AI Runner evaluation testing.

Provides fixtures to automatically start/stop the headless AI Runner server
and create client instances for testing.

Usage:
    def test_llm_generation(airunner_client):
        response = airunner_client.generate("What is 2+2?")
        assert "4" in response["text"]
"""

import logging
import os
import subprocess
import sys
import time
import pytest
import requests
from typing import Generator
from airunner.components.eval.client import AIRunnerClient


logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def airunner_server() -> Generator[subprocess.Popen, None, None]:
    """Start headless AI Runner server for testing session.

    This fixture:
    1. Starts the headless server in a subprocess
    2. Waits for the /health endpoint to respond
    3. Yields control to tests
    4. Terminates the server on session cleanup

    Yields:
        subprocess.Popen: The server process

    Raises:
        RuntimeError: If server fails to start within timeout
    """
    # Use environment variable for port, default to 8188
    port = int(os.environ.get("AIRUNNER_HTTP_PORT", "8188"))
    host = os.environ.get("AIRUNNER_HTTP_HOST", "127.0.0.1")

    # Start headless server
    env = os.environ.copy()
    env["AIRUNNER_HEADLESS"] = "1"
    env["AIRUNNER_HTTP_PORT"] = str(port)
    env["AIRUNNER_HTTP_HOST"] = host

    logger.info(f"Starting headless server on {host}:{port}")

    process = subprocess.Popen(
        [sys.executable, "-m", "airunner.bin.airunner_headless"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready (max 30 seconds)
    base_url = f"http://{host}:{port}"
    start_time = time.time()
    timeout = 30
    ready = False

    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{base_url}/health", timeout=1)
            if response.status_code == 200:
                ready = True
                logger.info("Server is ready")
                break
        except requests.RequestException:
            pass
        time.sleep(0.5)

    if not ready:
        # Server failed to start, kill it and get error output
        process.terminate()
        stdout, stderr = process.communicate(timeout=5)
        error_msg = (
            f"Server failed to start within {timeout}s\n"
            f"stdout: {stdout.decode()}\n"
            f"stderr: {stderr.decode()}"
        )
        raise RuntimeError(error_msg)

    yield process

    # Cleanup: terminate server
    logger.info("Terminating headless server")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        logger.warning("Server did not terminate gracefully, killing")
        process.kill()
        process.wait()


@pytest.fixture(scope="session")
def airunner_client(airunner_server) -> AIRunnerClient:
    """Create AIRunnerClient instance connected to test server.

    Depends on airunner_server fixture to ensure server is running.

    Args:
        airunner_server: The running server process (dependency)

    Returns:
        AIRunnerClient: Configured client instance
    """
    port = int(os.environ.get("AIRUNNER_HTTP_PORT", "8188"))
    host = os.environ.get("AIRUNNER_HTTP_HOST", "127.0.0.1")
    base_url = f"http://{host}:{port}"

    client = AIRunnerClient(base_url=base_url)

    # Verify client can connect
    try:
        client.health_check()
    except Exception as e:
        pytest.fail(f"Failed to connect to server: {e}")

    return client


@pytest.fixture
def airunner_client_function_scope(airunner_server) -> AIRunnerClient:
    """Create function-scoped AIRunnerClient instance.

    Use this fixture when you need a fresh client for each test function.
    The server remains running (session scope), but the client is recreated.

    Args:
        airunner_server: The running server process (dependency)

    Returns:
        AIRunnerClient: New client instance
    """
    port = int(os.environ.get("AIRUNNER_HTTP_PORT", "8188"))
    host = os.environ.get("AIRUNNER_HTTP_HOST", "127.0.0.1")
    base_url = f"http://{host}:{port}"

    return AIRunnerClient(base_url=base_url)
