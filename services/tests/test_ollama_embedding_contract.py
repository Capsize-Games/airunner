"""Deterministic tests for the local Ollama embedding contracts."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from airunner_services.api.routes.legacy_ollama_compat import (
    ollama_embed,
    ollama_embeddings,
)
from airunner_services.llm.companion.embeddings import EmbeddingModelIdentity
from airunner_services.runtimes.local_embeddings import LocalEmbeddingClient

_DIMENSION = 1024


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


def test_initialized_e5_embedder_requires_matching_model_path(tmp_path) -> None:
    embedder = _FakeLocalEmbedder()
    embedder.model_name = str(
        tmp_path / "text/models/llm/embedding/intfloat/e5-large"
    )
    request = _request(embedder, injected=False, base_path=str(tmp_path))

    response = ollama_embed({"input": "already loaded"}, request)

    assert response["model"] == "intfloat/e5-large"
    assert embedder.calls == [["already loaded"]]


def test_initialized_non_e5_model_is_unavailable(tmp_path) -> None:
    embedder = _FakeLocalEmbedder()
    embedder.model_name = str(tmp_path / "unrelated-model")
    request = _request(embedder, injected=False, base_path=str(tmp_path))

    with pytest.raises(HTTPException) as error:
        ollama_embed({"input": "hello"}, request)

    assert error.value.status_code == 503


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
