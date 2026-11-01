"""Ollama embedding contracts backed by an explicit local provider.

An embedding client may be installed by daemon assembly as
``req.app.state.local_embedding_client``. The fallback uses only an already
initialized ``llm._embedding`` whose ``model_name`` matches the configured E5
Large model path; it never touches the lazy ``llm.embedding`` property.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

from airunner_services.llm.companion.embeddings import EmbeddingModelIdentity
from airunner_services.runtimes.local_embeddings import (
    E5_LARGE_MODEL_ID,
    E5_LARGE_REVISION,
    LocalEmbeddingClient,
    MAX_EMBED_TEXT_CHARS,
)

from .legacy_common import get_airunner_app

logger = logging.getLogger(__name__)

MAX_EMBED_INPUTS = 64
E5_LARGE_DIMENSION = 1024
E5_LARGE_RELATIVE_PATH = Path(
    "text/models/llm/embedding/intfloat/e5-large"
)


def _invalid_request(detail: str = "invalid_embed_input") -> HTTPException:
    """Build one Ollama-compatible invalid-request error."""
    return HTTPException(status_code=400, detail=detail)


def _embedding_inputs(body: dict[str, Any], *, legacy: bool) -> list[str]:
    """Validate and normalize one Ollama embedding request's text input."""
    raw_input = (
        body.get("prompt", body.get("input"))
        if legacy
        else body.get("input", body.get("prompt"))
    )
    inputs = raw_input if isinstance(raw_input, list) else [raw_input]
    if raw_input is None or not inputs or len(inputs) > MAX_EMBED_INPUTS:
        raise _invalid_request()
    if any(not isinstance(text, str) for text in inputs):
        raise _invalid_request()
    if any(not text.strip() for text in inputs):
        raise _invalid_request()
    if any(len(text) > MAX_EMBED_TEXT_CHARS for text in inputs):
        raise _invalid_request("embed_input_too_large")
    if legacy and len(inputs) != 1:
        raise _invalid_request()
    return inputs


def _unavailable() -> HTTPException:
    """Build the stable error used when no supported local provider exists."""
    return HTTPException(
        status_code=503, detail="local_embedding_unavailable"
    )


def _e5_identity() -> EmbeddingModelIdentity:
    """Return the existing explicit E5 model identity."""
    return EmbeddingModelIdentity(
        model_id=E5_LARGE_MODEL_ID,
        revision=E5_LARGE_REVISION,
        dimension=E5_LARGE_DIMENSION,
    )


def _initialized_e5_client(req: Request) -> LocalEmbeddingClient:
    """Wrap the initialized RAG embedder only when its model path is E5."""
    app = get_airunner_app(req)
    llm = getattr(app, "llm", None)
    if llm is None:
        raise _unavailable()
    embedder = getattr(llm, "_embedding", None)
    path_settings = getattr(llm, "path_settings", None)
    base_path = getattr(path_settings, "base_path", None)
    model_name = getattr(embedder, "model_name", None)
    if embedder is None or not base_path or not model_name:
        raise _unavailable()
    expected_path = (Path(base_path).expanduser() / E5_LARGE_RELATIVE_PATH).resolve()
    actual_path = Path(model_name).expanduser().resolve()
    if actual_path != expected_path:
        raise _unavailable()
    try:
        return LocalEmbeddingClient(embedder, _e5_identity())
    except (TypeError, ValueError) as exc:
        logger.warning("Initialized E5 embedder is unusable: %s", exc)
        raise _unavailable() from exc


def _local_embedding_client(req: Request) -> LocalEmbeddingClient:
    """Resolve an injected client or an already initialized local E5 model.

    Daemon assembly may inject a ``LocalEmbeddingClient`` as
    ``req.app.state.local_embedding_client``. An explicitly configured remote
    RAG endpoint is not used by these Ollama routes.
    """
    injected = getattr(req.app.state, "local_embedding_client", None)
    if injected is not None:
        if not isinstance(injected, LocalEmbeddingClient):
            raise _unavailable()
        return injected
    if os.environ.get("AIRUNNER_EMBED_ENDPOINT", "").strip():
        raise _unavailable()
    try:
        return _initialized_e5_client(req)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Local embedding provider is unavailable: %s", exc)
        raise _unavailable() from exc


def handle_ollama_embedding(
    body: dict[str, Any], req: Request, *, legacy: bool
) -> dict[str, Any]:
    """Run one validated request and preserve each endpoint's response shape."""
    inputs = _embedding_inputs(body, legacy=legacy)
    requested_model = body.get("model")
    if requested_model is not None and (
        not isinstance(requested_model, str) or not requested_model.strip()
    ):
        raise _invalid_request("invalid_embed_model")
    client = _local_embedding_client(req)
    if requested_model is not None and requested_model != client.identity.model_id:
        raise HTTPException(status_code=404, detail="model_not_found")
    try:
        vectors = client.embed_documents(inputs)
        if len(vectors) != len(inputs):
            raise ValueError("embedding provider returned an invalid batch")
    except Exception as exc:
        logger.warning("Local embedding request failed: %s", exc)
        raise _unavailable() from exc
    if legacy:
        return {"embedding": vectors[0]}
    return {"model": client.identity.model_id, "embeddings": vectors}


__all__ = ["handle_ollama_embedding"]
