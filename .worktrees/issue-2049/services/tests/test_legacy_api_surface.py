"""Compatibility route smoke tests for the sunset legacy HTTP surface.

These tests verify that the versioned FastAPI surface now serves the Ollama
``/api/*``, OpenAI ``/v1/*``, and native legacy paths that previously lived in
the retired ``BaseHTTPRequestHandler`` server.
"""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from airunner_services.api.server import create_app


class _FakeApp:
    """Minimal app surface for compatibility routes that never need an LLM."""

    def __init__(self) -> None:
        self.llm = None

    def emit_signal(self, _code, _data=None) -> None:
        """Ignore signal emissions during metadata-only tests."""


def _client() -> TestClient:
    """Return a TestClient bound to a fresh FastAPI app."""
    os.environ["AIRUNNER_INSECURE_NO_AUTH"] = "1"
    app = create_app(
        allowed_origins=["http://localhost"],
        enable_cors=False,
        app_instance=_FakeApp(),
    )
    return TestClient(app)


def test_ollama_metadata_endpoints() -> None:
    """Ollama read-only metadata endpoints answer through FastAPI."""
    client = _client()

    response = client.get("/api/version")
    assert response.status_code == 200
    assert response.json() == {"version": "0.9.0"}

    response = client.get("/api/tags")
    assert response.status_code == 200
    assert isinstance(response.json().get("models"), list)

    response = client.get("/api/ps")
    assert response.status_code == 200
    assert response.json() == {"models": []}

    response = client.post("/api/show", json={"name": "airunner:latest"})
    assert response.status_code == 200
    assert "modelfile" in response.json()


def test_ollama_utility_endpoints() -> None:
    """Ollama utility endpoints answer through FastAPI."""
    client = _client()

    response = client.post("/api/copy", json={})
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

    response = client.post(
        "/api/embed", json={"input": ["hello"], "model": "airunner:latest"}
    )
    assert response.status_code == 200
    assert len(response.json()["embeddings"]) == 1

    response = client.post("/api/embeddings", json={"input": "hello"})
    assert response.status_code == 200
    assert len(response.json()["embeddings"]) == 1

    response = client.post("/api/pull", json={"model": "airunner:latest", "stream": False})
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

    response = client.post("/api/create", json={"stream": False})
    assert response.status_code == 200
    assert response.json() == {"status": "success"}


def test_openai_models_endpoint() -> None:
    """OpenAI /v1/models answers through FastAPI."""
    client = _client()
    response = client.get("/v1/models")
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "list"
    assert body["data"][0]["id"] == "airunner"


def test_legacy_native_paths_registered() -> None:
    """The native legacy paths are registered on the FastAPI surface."""
    client = _client()

    # /llm without a prompt fails validation, proving the route exists.
    response = client.post("/llm", json={"prompt": ""})
    assert response.status_code in {400, 422}

    response = client.post("/llm/generate_batch", json={"prompts": []})
    assert response.status_code == 400

    response = client.post("/stt", json={})
    assert response.status_code == 400

    response = client.post("/tts", json={})
    assert response.status_code == 400


def test_health_and_daemon_status_still_work() -> None:
    """/health and daemon status keep working on the versioned surface."""
    client = _client()

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "healthy"}

    response = client.get("/api/v1/health/daemon")
    assert response.status_code == 200
    assert "lifecycle_initialized" in response.json()
