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
import socket
import subprocess
import sys
import time
from typing import Generator

import pytest
import requests

from airunner.components.eval.client import AIRunnerClient


logger = logging.getLogger(__name__)


def _find_available_port(host: str) -> int:
    """Find an available TCP port on the given host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.getsockname()[1]


def _start_server_process(port: int, host: str):
    """Start the headless server subprocess."""
    env = os.environ.copy()
    env["AIRUNNER_HEADLESS"] = "1"
    env["AIRUNNER_HTTP_PORT"] = str(port)
    env["AIRUNNER_HTTP_HOST"] = host

    # Pass test-related environment variables to subprocess
    test_env_vars = [
        "AIRUNNER_DATABASE_URL",
        "AIRUNNER_ENVIRONMENT",
        "AIRUNNER_TEST_MODEL_PATH",
    ]
    for var in test_env_vars:
        if var in os.environ:
            env[var] = os.environ[var]

    logger.info(f"Starting headless server on {host}:{port}")
    server_log = open("/tmp/airunner_test_server.log", "w")

    return (
        subprocess.Popen(
            [sys.executable, "-m", "airunner.bin.airunner_headless"],
            env=env,
            stdout=server_log,
            stderr=subprocess.STDOUT,
        ),
        server_log,
    )


def _wait_for_server_health(base_url: str, timeout: int = 30) -> bool:
    """Poll server health endpoint until ready or timeout."""
    start_time = time.time()
    logger.info(f"Waiting for server at {base_url}/health to be ready...")

    while time.time() - start_time < timeout:
        try:
            logger.debug(
                f"Attempting health check "
                f"({time.time() - start_time:.1f}s elapsed)..."
            )
            response = requests.get(f"{base_url}/health", timeout=1)
            logger.debug(f"Health check response: {response.status_code}")
            if response.status_code == 200:
                logger.info("Server is ready!")
                return True
        except requests.RequestException as e:
            logger.debug(f"Health check failed: {e}")
        time.sleep(0.5)

    return False


def _terminate_server_process(process: subprocess.Popen):
    """Gracefully terminate server process."""
    logger.info("Terminating headless server")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        logger.warning("Server did not terminate gracefully, killing")
        process.kill()


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
    host = os.environ.get("AIRUNNER_HTTP_HOST", "127.0.0.1")
    port_env = os.environ.get("AIRUNNER_HTTP_PORT")
    if port_env:
        port = int(port_env)
    else:
        port = _find_available_port(host)
        os.environ["AIRUNNER_HTTP_PORT"] = str(port)

    base_url = f"http://{host}:{port}"
    timeout = (
        120  # Increased from 30 to 120 seconds to allow model loading time
    )

    process, server_log = _start_server_process(port, host)

    ready = _wait_for_server_health(base_url, timeout)

    if not ready:
        process.terminate()
        process.wait(timeout=5)
        server_log.close()
        with open("/tmp/airunner_test_server.log", "r") as f:
            log_content = f.read()
        error_msg = (
            f"Server failed to start within {timeout}s\n"
            f"Server log:\n{log_content}"
        )
        raise RuntimeError(error_msg)

    yield process

    _terminate_server_process(process)
    server_log.close()


@pytest.fixture(scope="session")
def airunner_client(
    airunner_server: subprocess.Popen,
) -> AIRunnerClient:
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
def airunner_client_function_scope(
    airunner_server: subprocess.Popen,
) -> AIRunnerClient:
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
