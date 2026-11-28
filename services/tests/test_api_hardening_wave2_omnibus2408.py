"""Wave-2 LOWs omnibus (#2408) regression tests.

Covers the omnibus items that the wave-2 route/server suites do not pin
down directly: the global exception handler hides internals behind a
correlation id, /api/pull|copy|create never report fake success, and the
blocking LLM / setup paths sit behind per-route admission budgets.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from airunner_services.api.admission_middleware import AdmissionMiddleware
from airunner_services.api.server import create_app


def _client(monkeypatch) -> TestClient:
    """Return a TestClient with auth disabled."""
    monkeypatch.setenv("AIRUNNER_API_KEY", "")
    monkeypatch.setenv("AIRUNNER_INSECURE_NO_AUTH", "1")
    return TestClient(
        create_app(
            allowed_origins=["http://localhost"],
            enable_cors=False,
        ),
        raise_server_exceptions=False,
    )


def test_global_handler_hides_detail_behind_correlation_id(
    monkeypatch,
) -> None:
    """Unhandled errors answer generic 500s keyed by correlation id."""
    client = _client(monkeypatch)

    @client.app.get("/_omnibus_boom")
    def _boom() -> dict:
        raise RuntimeError("secret-internals-marker")

    response = client.get("/_omnibus_boom")
    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "Internal server error"
    assert isinstance(body["correlation_id"], str)
    assert len(body["correlation_id"]) == 12
    assert "secret-internals-marker" not in response.text


def test_ollama_model_management_never_reports_fake_success(
    monkeypatch,
) -> None:
    """copy/create are 501; pull of an unknown model is 404, never 200."""
    client = _client(monkeypatch)
    assert client.post("/api/copy", json={}).status_code == 501
    assert client.post("/api/create", json={}).status_code == 501
    response = client.post(
        "/api/pull", json={"model": "no-such-model-xyz"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "model_not_found"


def test_wave2_blocking_paths_share_admission_budgets(monkeypatch) -> None:
    """POSTs to chat/generate/install/pull are budgeted; GETs are not."""
    monkeypatch.setenv("AIRUNNER_HTTP_MAX_INFLIGHT", "4")
    monkeypatch.setenv("AIRUNNER_SETUP_MAX_INFLIGHT", "1")

    async def _app(scope, receive, send) -> None:  # pragma: no cover
        raise AssertionError("must not be called")

    middleware = AdmissionMiddleware(_app)

    def _budget(path: str):
        return middleware._budget(
            {"type": "http", "method": "POST", "path": path}
        )

    chat = _budget("/api/chat")
    assert chat is middleware.generation
    assert _budget("/api/generate") is middleware.generation
    assert _budget("/v1/chat/completions") is middleware.generation
    assert _budget("/api/v1/install") is middleware.setup
    assert _budget("/api/pull") is middleware.setup
    assert (
        middleware._budget(
            {"type": "http", "method": "GET", "path": "/api/chat"}
        )
        is None
    )
