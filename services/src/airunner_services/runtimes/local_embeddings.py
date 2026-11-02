"""Local-only embedding runtime adapter (release B04).

Adapts an injected local embedding runtime — currently Intfloat E5 Large
(``intfloat/e5-large``) constructed with ``local_files_only`` by the
existing RAG stack (``llm/managers/agent/mixins/rag_properties_mixin.py``)
— to the shared embedding identity contract. Companion memory search and
other consumers can use the same local model without adding a second path.

The adapter never loads a model, never downloads, and never dials a
remote endpoint: it wraps an already-constructed embedder
(duck-typed ``embed_query``/``embed_documents``, the
``HuggingFaceEmbeddings`` shape), stamps every call with an explicit
``EmbeddingModelIdentity``, and validates each produced vector's
width against it. A remote embedder (the opt-in
``AIRUNNER_EMBED_ENDPOINT`` Ollama path, or any OpenAI-compatible
one) is refused at construction — this client is local-only by
construction, not by configuration.

No torch/langchain or companion import here: the embedder arrives injected,
and the identity/error contracts are defined in the neutral runtime layer.
"""

from __future__ import annotations

import math
from typing import Any, List

from airunner_services.runtimes.embedding_contracts import (
    ERROR_EMBEDDING_SPACE_MISMATCH,
    EmbeddingModelIdentity,
    ServiceError,
    ServiceErrorCode,
)

#: Selected local embedding model (R02 manifest, hardware-models.md §2;
#: default catalog entry in ``bootstrap/model_bootstrap_data.py``).
E5_LARGE_MODEL_ID = "intfloat/e5-large"

#: Pinned branch for the selected model (same sources as above).
E5_LARGE_REVISION = "4dc6d853a804b9c8886ede6dda8a073b7dc08a81"

#: Attribute only a remote-endpoint embedder carries
#: (``langchain_ollama.OllamaEmbeddings.base_url``).
_REMOTE_ATTRIBUTES = ("base_url", "api_base", "api_key")

#: Class-name markers of remote/provider embedders, lowercased.
_REMOTE_CLASS_MARKERS = ("ollama", "openai", "openrouter", "remote")

#: Largest single text embedded in one call; oversized input is rejected
#: instead of being tokenized and encoded unbounded.
MAX_EMBED_TEXT_CHARS = 8 * 1024

#: Largest batch embedded in one embed_documents call.
MAX_EMBED_BATCH_SIZE = 256


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
        bounded = [self._checked_text(text) for text in list(texts)]
        if len(bounded) > MAX_EMBED_BATCH_SIZE:
            raise ValueError(
                f"embed batch of {len(bounded)} exceeds "
                f"{MAX_EMBED_BATCH_SIZE}"
            )
        vectors = self._embedder.embed_documents(bounded)
        return [self._checked(vector) for vector in vectors]

    def embed_query(self, text: str) -> List[float]:
        """Embed one query; rejects an off-width vector fail-closed."""
        return self._checked(
            self._embedder.embed_query(self._checked_text(text))
        )

    @staticmethod
    def _checked_text(text: str) -> str:
        """Reject one oversized embedding input before tokenization."""
        if not isinstance(text, str):
            raise TypeError("embedding input must be a string")
        if len(text) > MAX_EMBED_TEXT_CHARS:
            raise ValueError(
                f"embedding input of {len(text)} chars exceeds "
                f"{MAX_EMBED_TEXT_CHARS}"
            )
        return text

    def _checked(self, vector: List[float]) -> List[float]:
        if len(vector) != int(self._identity.dimension):
            raise ServiceError(
                ServiceErrorCode(
                    code=ERROR_EMBEDDING_SPACE_MISMATCH,
                    detail=f"expected dim={self._identity.dimension}, "
                    f"found dim={len(vector)}",
                )
            )
        values = [float(value) for value in vector]
        if any(not math.isfinite(value) for value in values):
            raise ValueError("embedding vector contains a non-finite value")
        return values


def _type_has_attribute(embedder_type: type, attribute: str) -> bool:
    """Return True when one attribute is defined on the embedder type.

    Inspects the type MRO instead of the instance so evaluating the
    probe never executes arbitrary descriptor or __getattr__ code on a
    hostile embedder object.
    """
    return any(attribute in klass.__dict__ for klass in embedder_type.__mro__)


def _require_local_embedder(embedder: Any) -> None:
    """Refuse remote-endpoint embedders (explicit remote stays opt-in
    elsewhere; this client never dials out)."""
    embedder_type = type(embedder)
    for attribute in _REMOTE_ATTRIBUTES:
        if _type_has_attribute(embedder_type, attribute):
            raise ValueError(
                "refusing remote embedding endpoint "
                f"(found {attribute!r} on {embedder_type.__name__})"
            )
    class_name = embedder_type.__name__.lower()
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
