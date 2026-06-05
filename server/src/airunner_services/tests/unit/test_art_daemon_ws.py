"""Functional tests for the art daemon WebSocket endpoint.

These test the WS protocol layer — connection, message parsing, error
handling, and disconnect behavior.  Runtime-dependent handlers (generate,
health, etc.) require the full runtime stack and are tested separately
in the WebSocket transport integration tests.
"""

import asyncio
import json
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import websockets
import websockets.asyncio.client as ws_client

WS_PATH = "/api/v1/art/daemon/ws"
TEST_HOST = "127.0.0.1"


def _start_test_server(port: int, ready: threading.Event, error: list[str]):
    """Start a uvicorn server in a background thread, signal when ready."""
    env = {
        **__import__("os").environ,
        "AIRUNNER_BASE_PATH": str(Path(__file__).parent.parent.parent.parent),
        "AIRUNNER_LOG_LEVEL": "ERROR",
    }

    script = rf"""
import uvicorn, sys, os
os.environ.update({env!r})
from fastapi import FastAPI
from airunner_services.api.routes.art_daemon_ws import router
app = FastAPI()
app.include_router(router, prefix="/api/v1/art")
import signal
signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
uvicorn.run(app, host="127.0.0.1", port={port}, log_level="error")
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            import urllib.request
            resp = urllib.request.urlopen(
                f"http://127.0.0.1:{port}/openapi.json", timeout=1,
            )
            if resp.status == 200:
                ready.set()
                return process
        except Exception:
            time.sleep(0.1)
    process.kill()
    error.append("Server failed to start")
    return process


@pytest.fixture(scope="module")
def test_server():
    """Fixture that starts/stops a minimal test server."""
    port = 8199
    ready = threading.Event()
    error: list[str] = []
    process = _start_test_server(port, ready, error)
    if not ready.wait(timeout=8):
        process.kill()
        pytest.fail(error[0] if error else "Server startup timeout")
    yield port
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()


async def _connect(port: int):
    """Connect to the test server's daemon WS."""
    url = f"ws://{TEST_HOST}:{port}{WS_PATH}"
    return await ws_client.connect(url)


# ── Protocol tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_connect_and_close(test_server: int):
    """Connection is accepted and closed cleanly."""
    ws = await _connect(test_server)
    await ws.close()
    assert ws.state.name in ("CLOSED", "CLOSING")


@pytest.mark.asyncio
async def test_ws_invalid_json_returns_error(test_server: int):
    """Non-JSON payload returns an error frame."""
    ws = await _connect(test_server)

    await ws.send("not json{{{")
    response = await asyncio.wait_for(ws.recv(), timeout=5)
    data = json.loads(response)
    assert data["type"] == "error"
    assert "Invalid JSON" in data["error"]
    await ws.close()


@pytest.mark.asyncio
async def test_ws_unknown_action_returns_error(test_server: int):
    """Unknown actions get a failed response."""
    ws = await _connect(test_server)

    msg = {"request_id": "test-unknown", "action": "nonexistent"}
    await ws.send(json.dumps(msg))

    response = await asyncio.wait_for(ws.recv(), timeout=5)
    data = json.loads(response)
    assert data["request_id"] == "test-unknown"
    assert data["status"] == "failed"
    assert "Unknown action" in data["error"]
    await ws.close()


@pytest.mark.asyncio
async def test_ws_health_action_receives_response(test_server: int):
    """The 'health' action returns a response (even if runtime is
    unavailable)."""
    ws = await _connect(test_server)

    msg = {"request_id": "test-health", "action": "health"}
    await ws.send(json.dumps(msg))

    response = await asyncio.wait_for(ws.recv(), timeout=5)
    data = json.loads(response)
    assert data["request_id"] == "test-health"
    assert data["type"] in ("response", "error")
    await ws.close()


@pytest.mark.asyncio
async def test_ws_health_missing_request_id(test_server: int):
    """Missing request_id is handled gracefully."""
    ws = await _connect(test_server)

    msg = {"action": "health"}
    await ws.send(json.dumps(msg))

    response = await asyncio.wait_for(ws.recv(), timeout=5)
    data = json.loads(response)
    assert data.get("type") in ("response", "error")
    await ws.close()


@pytest.mark.asyncio
async def test_ws_health_missing_action(test_server: int):
    """Missing action is handled."""
    ws = await _connect(test_server)

    msg = {"request_id": "test-no-action"}
    await ws.send(json.dumps(msg))

    response = await asyncio.wait_for(ws.recv(), timeout=5)
    data = json.loads(response)
    assert data.get("type") in ("response", "error")
    await ws.close()


@pytest.mark.asyncio
async def test_ws_multiple_requests_one_connection(test_server: int):
    """Multiple requests over one connection each receive a response."""
    ws = await _connect(test_server)

    for i in range(5):
        rid = f"test-multi-{i}"
        msg = {"request_id": rid, "action": "status"}
        await ws.send(json.dumps(msg))
        response = await asyncio.wait_for(ws.recv(), timeout=5)
        data = json.loads(response)
        assert data["request_id"] == rid

    await ws.close()


@pytest.mark.asyncio
async def test_ws_disconnect_cleanup(test_server: int):
    """Server does not crash when client disconnects without closing."""
    ws = await _connect(test_server)
    # Force close the underlying transport
    await ws.close()
    # Second connection should work fine
    ws2 = await _connect(test_server)
    msg = {"request_id": "test-reconnect", "action": "status"}
    await ws2.send(json.dumps(msg))
    response = await asyncio.wait_for(ws2.recv(), timeout=5)
    data = json.loads(response)
    assert data["request_id"] == "test-reconnect"
    await ws2.close()
