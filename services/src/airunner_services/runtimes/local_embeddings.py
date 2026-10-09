"""Local-only embedding runtime adapter (release B04).

Adapts the selected local embedding runtime — Intfloat E5 Large
(``intfloat/e5-large``) constructed with ``local_files_only`` by the
existing RAG stack (``llm/managers/agent/mixins/rag_properties_mixin.py``)
— to the B01 ``CompanionEmbeddingClient`` contract, so companion
memory search (B05) embeds through the same local model the rest of
Desktop already uses instead of growing a second embedding path.

The adapter never loads a model, never downloads, and never dials a
remote endpoint: it wraps an already-constructed embedder
(duck-typed ``embed_query``/``embed_documents``, the
``HuggingFaceEmbeddings`` shape), stamps every call with an explicit
``EmbeddingModelIdentity``, and validates each produced vector's
width against it. A remote embedder (the opt-in
``AIRUNNER_EMBED_ENDPOINT`` Ollama path, or any OpenAI-compatible
one) is refused at construction — this client is local-only by
construction, not by configuration.

No torch/langchain import here: the embedder arrives injected, so
this module (and its companion contract import) stays free of the
heavy ML runtime.
"""

from __future__ import annotations

from typing import Any, List

from airunner_services.llm.companion.contracts import (
    ERROR_EMBEDDING_SPACE_MISMATCH,
    CompanionError,
    CompanionErrorCode,
)
from airunner_services.llm.companion.embeddings import EmbeddingModelIdentity

#: Selected local embedding model (R02 manifest, hardware-models.md §2;
#: default catalog entry in ``bootstrap/model_bootstrap_data.py``).
E5_LARGE_MODEL_ID = "intfloat/e5-large"

#: Pinned branch for the selected model (same sources as above).
E5_LARGE_REVISION = "main"

#: Attribute only a remote-endpoint embedder carries
#: (``langchain_ollama.OllamaEmbeddings.base_url``).
_REMOTE_ATTRIBUTES = ("base_url", "api_base", "api_key")

#: Class-name markers of remote/provider embedders, lowercased.
_REMOTE_CLASS_MARKERS = ("ollama", "openai", "openrouter", "remote")


class LocalEmbeddingClient:
    """A ``CompanionEmbeddingClient`` over one local embedder.

    Structurally satisfies the Protocol (duck-typed, like the
    existing RAG retriever's use of its embedding model) without
    importing it, keeping this module independent of langchain.
    """

    def __init__(
        self, embedder: Any, identity: EmbeddingModelIdentity
    ) -> None:
        _require_local_embedder(embedder)
        _require_embedder_shape(embedder)
        self._embedder = embedder
        self._identity = identity

    @property
    def identity(self) -> EmbeddingModelIdentity:
        return self._identity

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed texts; rejects an off-width vector fail-closed."""
        vectors = self._embedder.embed_documents(list(texts))
        return [self._checked(vector) for vector in vectors]

    def embed_query(self, text: str) -> List[float]:
        """Embed one query; rejects an off-width vector fail-closed."""
        return self._checked(self._embedder.embed_query(text))

    def _checked(self, vector: List[float]) -> List[float]:
        if len(vector) != int(self._identity.dimension):
            raise CompanionError(
                CompanionErrorCode(
                    code=ERROR_EMBEDDING_SPACE_MISMATCH,
                    detail=f"expected dim={self._identity.dimension}, "
                    f"found dim={len(vector)}",
                )
            )
        return [float(value) for value in vector]


def _require_local_embedder(embedder: Any) -> None:
    """Refuse remote-endpoint embedders (explicit remote stays opt-in
    elsewhere; this client never dials out)."""
    for attribute in _REMOTE_ATTRIBUTES:
        if hasattr(embedder, attribute):
            raise ValueError(
                "refusing remote embedding endpoint "
                f"(found {attribute!r} on {type(embedder).__name__})"
            )
    class_name = type(embedder).__name__.lower()
    if any(marker in class_name for marker in _REMOTE_CLASS_MARKERS):
        raise ValueError(f"refusing remote embedding endpoint ({class_name})")


def _require_embedder_shape(embedder: Any) -> None:
    """Require the local ``HuggingFaceEmbeddings`` call shape."""
    for method in ("embed_query", "embed_documents"):
        if not callable(getattr(embedder, method, None)):
            raise TypeError(
                f"embedder {type(embedder).__name__} lacks {method}()"
            )


__all__ = [
    "E5_LARGE_MODEL_ID",
    "E5_LARGE_REVISION",
    "LocalEmbeddingClient",
]
