"""Compatibility route smoke tests for the sunset legacy HTTP surface.

These tests verify that the versioned FastAPI surface now serves the Ollama
``/api/*``, OpenAI ``/v1/*``, and native legacy paths that previously lived in
the retired ``BaseHTTPRequestHandler`` server.
"""

from __future__ import annotations

import os
import time
from types import SimpleNamespace

from fastapi.testclient import TestClient

from airunner_common.contract_enums import ModelStatus, ModelType
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


def test_ollama_metadata_endpoints(monkeypatch) -> None:
    """Ollama read-only metadata endpoints answer through FastAPI."""
    from airunner_services.api.routes import legacy_ollama_compat

    monkeypatch.setattr(legacy_ollama_compat, "configured_model_basename", lambda: "qwen3.5-9b")
    monkeypatch.setattr(
        legacy_ollama_compat, "_configured_artifact_metadata", lambda: None
    )
    client = _client()

    response = client.get("/api/version")
    assert response.status_code == 200
    assert response.json() == {"version": "0.9.0"}

    response = client.get("/api/tags")
    assert response.status_code == 200
    assert response.json() == {"models": []}

    response = client.get("/api/ps")
    assert response.status_code == 200
    assert response.json() == {"models": []}

    response = client.post("/api/show", json={"model": "qwen3.5-9b"})
    assert response.status_code == 200
    assert response.json()["model_info"]["context_length"] == 262144
    assert "license" not in response.json()
    assert "details" not in response.json()


def test_tags_lists_configured_local_artifact_without_loading(
    monkeypatch, tmp_path
) -> None:
    """Installed local artifacts remain discoverable while the model is cold."""
    from airunner_services.database.models.llm_generator_settings import (
        LLMGeneratorSettings,
    )

    artifact = tmp_path / "Qwen3.5-9B-Q8_0.gguf"
    artifact.write_bytes(b"configured metadata fixture")
    monkeypatch.setattr(
        LLMGeneratorSettings,
        "_objects",
        SimpleNamespace(
            first=lambda: SimpleNamespace(
                model_path=str(artifact), model_id="qwen3.5-9b"
            )
        ),
    )
    client = _client()

    tags = client.get("/api/tags").json()["models"]
    processes = client.get("/api/ps").json()["models"]

    assert len(tags) == 1
    assert tags[0]["name"] == "qwen3.5-9b:latest"
    assert tags[0]["size"] == artifact.stat().st_size
    assert tags[0]["digest"] == ""
    assert tags[0]["details"]["quantization_level"] == "Q8_0"
    assert processes == []


def test_ollama_metadata_uses_loaded_manager_artifact_facts(
    monkeypatch, tmp_path
) -> None:
    """List/process metadata comes from the active manager, not settings guesses."""
    artifact = tmp_path / "Qwen3.5-9B-Q8_0.gguf"
    artifact.write_bytes(b"small metadata fixture")
    client = _client()
    app = client.app.state.airunner_app
    model_manager = SimpleNamespace(
        model_status={ModelType.LLM: ModelStatus.LOADED},
        _current_model_path=str(artifact),
        _resolve_model_id_from_path=lambda _path: "qwen3.5-9b",
        _chat_model=SimpleNamespace(n_ctx=32768),
    )
    worker = SimpleNamespace(
        current_model_status=lambda: ModelStatus.LOADED,
        _model_manager=model_manager,
    )
    app._worker_manager = SimpleNamespace(_llm_generate_worker=worker)

    tags = client.get("/api/tags").json()["models"]
    processes = client.get("/api/ps").json()["models"]

    assert len(tags) == len(processes) == 1
    listed = tags[0]
    running = processes[0]
    assert listed["name"] == "qwen3.5-9b:latest"
    assert listed["size"] == artifact.stat().st_size
    assert listed["digest"] == ""
    assert listed["modified_at"] != "2024-12-01T00:00:00.000000000Z"
    assert listed["details"]["parameter_size"] == "9B"
    assert listed["details"]["quantization_level"] == "Q8_0"
    assert running["size"] == artifact.stat().st_size
    assert running["size_vram"] == 0
    assert running["context_length"] == 32768
    assert running["expires_at"] == "0001-01-01T00:00:00.000000Z"


def test_ollama_unknown_usage_is_zero_and_total_duration_is_measured() -> None:
    """Missing token and phase timings are not estimated from text length."""
    from airunner_services.api.routes.legacy_ollama_compat import (
        _ollama_timings,
    )

    timings = _ollama_timings(time.monotonic() - 0.01)

    assert timings["total_duration"] > 0
    assert timings["load_duration"] == 0
    assert timings["prompt_eval_count"] == 0
    assert timings["prompt_eval_duration"] == 0
    assert timings["eval_count"] == 0
    assert timings["eval_duration"] == 0


def test_ollama_ps_uses_unloaded_worker_status_over_stale_references() -> None:
    """An unloaded manager must not be advertised from stale pointers/inventory."""
    client = _client()
    app = client.app.state.airunner_app

    worker = SimpleNamespace(
        current_model_status=lambda: ModelStatus.UNLOADED,
        _model_manager=SimpleNamespace(_chat_model=object()),
    )
    app._worker_manager = SimpleNamespace(_llm_generate_worker=worker)
    app.model_load_balancer = SimpleNamespace(
        get_loaded_models=lambda: [ModelType.LLM]
    )

    response = client.get("/api/ps")

    assert response.status_code == 200
    assert response.json() == {"models": []}

    app._worker_manager._llm_generate_worker.current_model_status = (
        lambda: ModelStatus.LOADED
    )
    client.app.state.lifecycle_service = SimpleNamespace(
        current_llm_model_status=lambda: ModelStatus.UNLOADED
    )
    response = client.get("/api/ps")
    assert response.status_code == 200
    assert response.json() == {"models": []}

    from airunner_services.api.routes.legacy_llm_compat import (
        is_llm_model_loaded,
    )

    app._worker_manager = SimpleNamespace(
        _llm_generate_worker=SimpleNamespace(
            _model_manager=SimpleNamespace(_chat_model=object())
        )
    )
    app.model_load_balancer = None
    assert is_llm_model_loaded(app) is False


def test_ollama_utility_endpoints() -> None:
    """Ollama utility endpoints answer through FastAPI."""
    client = _client()

    # Copy and model creation have no local implementation: they must
    # report 501, never a fake success payload.
    for path in ("/api/copy", "/api/create"):
        response = client.post(path, json={})
        assert response.status_code == 501

    # Pull without a model is a request error and must not queue work.
    response = client.post("/api/pull", json={})
    assert response.status_code == 400

    # This smoke app has no configured local embedding provider. Neither
    # Ollama endpoint may report success with invented placeholder vectors.
    response = client.post("/api/embed", json={"input": ["hello"]})
    assert response.status_code == 503
    assert response.json()["detail"] == "local_embedding_unavailable"

    response = client.post("/api/embeddings", json={"prompt": "hello"})
    assert response.status_code == 503
    assert response.json()["detail"] == "local_embedding_unavailable"

    response = client.post(
        "/api/embed", json={"input": ["x"] * 65}
    )
    assert response.status_code == 400


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
