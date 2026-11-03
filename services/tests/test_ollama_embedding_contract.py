"""Deterministic tests for the local Ollama embedding contracts."""

from __future__ import annotations

import asyncio
from concurrent.futures import Future
import threading
import time
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from airunner_services.api.routes.legacy_ollama_compat import (
    ollama_embed as _ollama_embed_route,
    ollama_embeddings as _ollama_embeddings_route,
)
from airunner_services.api.routes.ollama_embedding_helpers import (
    handle_ollama_embedding_async,
)
from airunner_services.llm.companion.embeddings import EmbeddingModelIdentity
from airunner_services.runtimes.local_embeddings import LocalEmbeddingClient
from airunner_services.runtimes import e5_model_identity as e5_identity_module
from airunner_services.runtimes.e5_model_identity import E5ModelIdentity, VerifiedE5Embedder

_DIMENSION = 1024


def ollama_embed(body: dict, req):
    """Run the async HTTP endpoint directly in synchronous contract tests."""
    return asyncio.run(_ollama_embed_route(body, req))


def ollama_embeddings(body: dict, req):
    """Run the async legacy HTTP endpoint in synchronous contract tests."""
    return asyncio.run(_ollama_embeddings_route(body, req))


class _FakeLocalEmbedder:
    """Return caller-visible fixed vectors without loading a model."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.vectors = [
            [float(index)] * _DIMENSION for index in range(1, 4)
        ]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return self.vectors[: len(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.vectors[0]


def _request(
    embedder: Any | None,
    *,
    injected: bool = True,
    base_path: str | None = None,
) -> SimpleNamespace:
    llm = SimpleNamespace(
        _embedding=embedder,
        path_settings=(
            SimpleNamespace(base_path=base_path) if base_path else None
        ),
    )
    service_app = SimpleNamespace(llm=llm)
    api_app = SimpleNamespace(
        state=SimpleNamespace(
            airunner_app=service_app,
            local_embedding_client=(
                LocalEmbeddingClient(
                    embedder,
                    EmbeddingModelIdentity(
                        model_id="intfloat/e5-large",
                        revision="main",
                        dimension=_DIMENSION,
                    ),
                )
                if injected and embedder is not None
                else None
            ),
        )
    )
    return SimpleNamespace(app=api_app)


def test_api_embed_uses_local_provider_and_ollama_batch_shape() -> None:
    embedder = _FakeLocalEmbedder()

    response = ollama_embed(
        {"model": "intfloat/e5-large", "input": ["one", "two"]},
        _request(embedder),
    )

    assert response == {
        "model": "intfloat/e5-large",
        "embeddings": embedder.vectors[:2],
    }
    assert embedder.calls == [["one", "two"]]
    assert not {"total_duration", "load_duration", "prompt_eval_count"} & (
        response.keys()
    )


def test_injected_embedder_does_not_block_the_async_event_loop() -> None:
    embedder = _FakeLocalEmbedder()
    inference_started = threading.Event()
    allow_inference = threading.Event()
    event_loop_progressed = threading.Event()
    observed_progress_before_release = []

    def blocking_embed_documents(texts: list[str]) -> list[list[float]]:
        embedder.calls.append(list(texts))
        inference_started.set()
        assert allow_inference.wait(timeout=3)
        return embedder.vectors[: len(texts)]

    embedder.embed_documents = blocking_embed_documents
    request = _request(embedder)

    def release_after_observing_blocked_inference() -> None:
        if inference_started.wait(timeout=3):
            time.sleep(0.1)
            observed_progress_before_release.append(
                event_loop_progressed.is_set()
            )
        allow_inference.set()

    releaser = threading.Thread(
        target=release_after_observing_blocked_inference
    )
    releaser.start()

    async def _run_route_and_heartbeat() -> dict[str, Any]:
        route_task = asyncio.create_task(
            handle_ollama_embedding_async(
                {"input": "blocked but isolated"}, request, legacy=False
            )
        )

        async def _heartbeat() -> None:
            await asyncio.sleep(0.02)
            event_loop_progressed.set()

        heartbeat_task = asyncio.create_task(_heartbeat())
        response = await route_task
        await heartbeat_task
        return response

    try:
        response = asyncio.run(_run_route_and_heartbeat())
    finally:
        allow_inference.set()
        releaser.join(timeout=3)

    assert not releaser.is_alive()
    assert observed_progress_before_release == [True]
    assert response["embeddings"] == embedder.vectors[:1]


def test_legacy_embeddings_uses_prompt_and_single_vector_shape() -> None:
    embedder = _FakeLocalEmbedder()

    response = ollama_embeddings(
        {"prompt": "legacy input"}, _request(embedder)
    )

    assert response == {"embedding": embedder.vectors[0]}
    assert embedder.calls == [["legacy input"]]


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"input": 42},
        {"input": ["valid", None]},
        {"input": "   "},
        {"input": "x" * 8193},
        {"input": ["x"] * 65},
    ],
)
def test_api_embed_rejects_invalid_or_unbounded_inputs(body: dict) -> None:
    with pytest.raises(HTTPException) as error:
        ollama_embed(body, _request(_FakeLocalEmbedder()))

    assert error.value.status_code == 400


def test_legacy_embeddings_rejects_multiple_inputs() -> None:
    with pytest.raises(HTTPException) as error:
        ollama_embeddings(
            {"prompt": ["one", "two"]}, _request(_FakeLocalEmbedder())
        )

    assert error.value.status_code == 400


def test_requested_model_must_match_configured_embedding_identity() -> None:
    with pytest.raises(HTTPException) as error:
        ollama_embed(
            {"model": "airunner:latest", "input": "hello"},
            _request(_FakeLocalEmbedder()),
        )

    assert error.value.status_code == 404
    assert error.value.detail == "model_not_found"


def test_unconfigured_local_provider_returns_503() -> None:
    class _LazyOnlyLLM:
        _embedding = None
        path_settings = None

        @property
        def embedding(self):
            raise AssertionError("lazy model property must not be read")

    request = _request(None, injected=False)
    request.app.state.airunner_app.llm = _LazyOnlyLLM()
    with pytest.raises(HTTPException) as error:
        ollama_embed({"input": "hello"}, request)

    assert error.value.status_code == 503
    assert error.value.detail == "local_embedding_unavailable"


def test_missing_e5_model_is_unavailable_without_phantom_download_signal(
    tmp_path, monkeypatch
) -> None:
    import logging

    from airunner_services.llm.managers.agent.mixins.rag_properties_mixin import (
        RAGPropertiesMixin,
    )
    from airunner_services.runtimes.e5_model_identity import E5ModelIdentityError

    monkeypatch.delenv("AIRUNNER_EMBED_ENDPOINT", raising=False)
    signals = []

    class _Properties(RAGPropertiesMixin):
        _embedding = None

        def __init__(self):
            self.path_settings = SimpleNamespace(base_path=str(tmp_path))
            self.logger = logging.getLogger("missing-e5-test")
            self.emit_signal = lambda *args: signals.append(args)

    from airunner_services.runtimes import e5_model_identity

    def _missing(_path):
        raise E5ModelIdentityError("model directory is incomplete")

    monkeypatch.setattr(e5_model_identity, "verify_e5_model_directory", _missing)

    assert _Properties().embedding is None
    assert signals == []


def test_explicit_remote_provider_is_not_used(monkeypatch) -> None:
    monkeypatch.setenv("AIRUNNER_EMBED_ENDPOINT", "http://remote.invalid")

    class _RemoteMustNotBeRead:
        _embedding = None
        path_settings = None

    request = _request(None)
    request.app.state.airunner_app.llm = _RemoteMustNotBeRead()
    with pytest.raises(HTTPException) as error:
        ollama_embed({"input": "hello"}, request)

    assert error.value.status_code == 503


def test_initialized_e5_embedder_requires_verified_identity(tmp_path) -> None:
    embedder = _FakeLocalEmbedder()
    embedder.model_name = str(
        tmp_path / "text/models/llm/embedding/intfloat/e5-large"
    )
    request = _request(embedder, injected=False, base_path=str(tmp_path))

    with pytest.raises(HTTPException) as error:
        ollama_embed({"input": "already loaded"}, request)

    assert error.value.status_code == 503
    assert embedder.calls == []


def test_initialized_verified_e5_embedder_is_accepted(tmp_path) -> None:
    embedder = _FakeLocalEmbedder()
    embedder.model_name = str(
        tmp_path / "text/models/llm/embedding/intfloat/e5-large"
    )
    files = tuple(
        sorted(
            (name, digest)
            for name, (_, digest) in e5_identity_module.E5_MODEL_FILES.items()
        )
    )
    identity = E5ModelIdentity(
        model_id=e5_identity_module.E5_LARGE_MODEL_ID,
        revision=e5_identity_module.E5_LARGE_REVISION,
        dimension=e5_identity_module.E5_LARGE_DIMENSION,
        manifest_sha256=e5_identity_module._manifest_digest(files),
        file_sha256=files,
    )
    request = _request(
        VerifiedE5Embedder(embedder, identity),
        injected=False,
        base_path=str(tmp_path),
    )

    response = ollama_embed({"input": "plain input"}, request)

    assert response["model"] == "intfloat/e5-large"
    assert embedder.calls == [["passage: plain input"]]


def test_initialized_non_e5_model_is_unavailable(tmp_path) -> None:
    embedder = _FakeLocalEmbedder()
    embedder.model_name = str(tmp_path / "unrelated-model")
    request = _request(embedder, injected=False, base_path=str(tmp_path))

    with pytest.raises(HTTPException) as error:
        ollama_embed({"input": "hello"}, request)

    assert error.value.status_code == 503


def test_worker_route_cancels_pending_embedding_on_client_cancellation() -> None:
    class _Worker:
        def __init__(self):
            self.future = Future()
            self.cancelled = []

        def submit_embedding_documents(self, _texts):
            return "request-1", self.future

        def cancel_embedding_request(self, request_id):
            self.cancelled.append(request_id)
            return self.future.cancel()

    worker = _Worker()
    request = _request(None, injected=False)
    request.app.state.airunner_app._llm_generate_worker = worker

    async def _cancel_pending_request():
        task = asyncio.create_task(
            handle_ollama_embedding_async(
                {"input": ["real request"]}, request, legacy=False
            )
        )
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(_cancel_pending_request())
    assert worker.cancelled == ["request-1"]
    assert worker.future.cancelled()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_local_embedding_client_rejects_non_finite_vectors(value: float) -> None:
    embedder = _FakeLocalEmbedder()
    embedder.vectors[0][17] = value
    client = LocalEmbeddingClient(
        embedder,
        EmbeddingModelIdentity(
            model_id="intfloat/e5-large",
            revision="main",
            dimension=_DIMENSION,
        ),
    )

    with pytest.raises(ValueError, match="non-finite"):
        client.embed_query("finite vector required")
