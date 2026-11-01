"""Exercise admission at the ASGI lifecycle and authentication boundaries."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from airunner_services.api.admission_middleware import AdmissionMiddleware
from airunner_services.api import admission_middleware
from airunner_services.api.server import create_app


async def _receive() -> dict:
    return {"type": "http.request", "body": b""}


def _scope(path: str = "/api/chat") -> dict:
    return {"type": "http", "method": "POST", "path": path}


def test_stream_holds_capacity_until_work_finishes(monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_HTTP_MAX_INFLIGHT", "1")

    async def scenario() -> None:
        started, finish = asyncio.Event(), asyncio.Event()

        async def app(scope, receive, send) -> None:
            await send({"type": "http.response.start", "status": 200})
            started.set()
            await finish.wait()

        middleware = AdmissionMiddleware(app)
        messages: list[dict] = []

        async def send(message: dict) -> None:
            messages.append(message)

        first = asyncio.create_task(middleware(_scope(), _receive, send))
        await started.wait()
        await middleware(_scope(), _receive, send)
        assert messages[-2]["status"] == 429
        finish.set()
        await first
        await middleware(_scope(), _receive, send)
        assert messages[-1]["status"] == 200

    asyncio.run(scenario())


def test_rate_limit_applies_after_completed_requests(monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_HTTP_REQUESTS_PER_MINUTE", "1")

    async def scenario() -> None:
        async def app(scope, receive, send) -> None:
            await send({"status": 200})

        middleware = AdmissionMiddleware(app)
        messages: list[dict] = []

        async def send(message: dict) -> None:
            messages.append(message)

        await middleware(_scope(), _receive, send)
        await middleware(_scope(), _receive, send)
        assert messages[-2]["status"] == 429

    asyncio.run(scenario())


def test_errors_release_active_slot(monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_HTTP_MAX_INFLIGHT", "1")

    async def scenario() -> None:
        async def app(scope, receive, send) -> None:
            raise RuntimeError("runtime failed")

        middleware = AdmissionMiddleware(app)
        for _ in range(2):
            with pytest.raises(RuntimeError, match="runtime failed"):
                await middleware(_scope(), _receive, _receive)

    asyncio.run(scenario())


def test_unauthorized_requests_do_not_consume_capacity(monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_API_KEY", "test-key")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "0")
    monkeypatch.setenv("AIRUNNER_HTTP_REQUESTS_PER_MINUTE", "1")
    monkeypatch.setattr(
        admission_middleware, "GENERATION_PATHS", {"/_admission_probe"}
    )
    monkeypatch.setattr(
        "airunner_services.api.server.mount_client_bundle", lambda app: False
    )
    app = create_app(enable_cors=False)

    @app.post("/_admission_probe")
    def fake_generate() -> dict:
        return {"done": True}

    client = TestClient(app)
    assert client.post("/_admission_probe").status_code == 401
    assert client.post("/_admission_probe").status_code == 401
    response = client.post(
        "/_admission_probe", headers={"x-api-key": "test-key"}
    )
    assert response.status_code == 200
