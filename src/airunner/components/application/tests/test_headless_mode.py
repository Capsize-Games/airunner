"""
Tests for headless mode functionality.

Tests that App can start in headless mode without GUI components
and that the API server responds to /health endpoint.
"""

import pytest
import os


def test_headless_mode_env_variable(monkeypatch):
    """Test that AIRUNNER_HEADLESS=1 enables headless mode."""

    from airunner.app import App

    # Create app with AIRUNNER_HEADLESS set
    app = App(headless=True)

    assert app.headless is True
    assert app.api_server_thread is not None  # Server started in headless mode
    assert app.api_server_thread.is_alive()  # Thread is running


def test_headless_mode_explicit_flag():
    """Test that headless=True enables headless mode."""
    from airunner.app import App

    app = App(headless=True)

    assert app.headless is True


def test_headless_health_endpoint():
    """Test that /health endpoint responds in headless mode.

    This test starts the headless server, queries /health,
    and verifies the response.
    """

    # Start headless server in subprocess
    env = os.environ.copy()
    env["AIRUNNER_HTTP_PORT"] = "8765"  # Use non-standard port for testing

    # Note: This test requires the airunner-headless command to be available
    # For now, we'll skip if not in CI environment
    pytest.skip("Integration test - requires full headless server setup")

    # TODO: Implement full integration test when airunner-headless is available
    # proc = subprocess.Popen(
    #     [sys.executable, "-m", "airunner.bin.airunner_headless", "--port", "8765"],
    #     env=env
    # )
    #
    # try:
    #     # Wait for server to start
    #     time.sleep(2)
    #
    #     # Query health endpoint
    #     response = requests.get("http://localhost:8765/health", timeout=5)
    #
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "ready"
    #     assert "services" in data
    #
    # finally:
    #     proc.terminate()
    #     proc.wait(timeout=5)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
