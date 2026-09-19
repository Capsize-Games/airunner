"""Structural interface (port) for the daemon's RAG capability.

RAG is currently delivered by ``RAGMixin`` composed directly into the LLM
model manager, so "the RAG manager" and "the LLM manager" are the same
object. That is fine while RAG lives inside ``airunner_services``, but it is
the specific coupling that blocks any future extraction of RAG into its own
package/repository: callers cannot depend on a RAG capability, only on the
manager that happens to also do RAG.

This module names the operations the rest of the daemon relies on, as a
``typing.Protocol``. It is deliberately **additive**: nothing is rewired
here. The manager-containment change (holding a ``RAGService`` instead of
being one) is the follow-up that this port exists to make mechanical.

Deliberately dependency-light: no LangChain, torch, or RAG mixin imports, so
this module can be imported by callers that must not pull the RAG runtime in
just to name the type.
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence, runtime_checkable

__all__ = ["RAGService", "RAG_SERVICE_METHODS"]

#: The method names that make up the port, in one place so the conformance
#: test and any future adapter agree on the surface.
RAG_SERVICE_METHODS: tuple[str, ...] = (
    "search",
    "ensure_indexed_files",
    "index_all_documents",
    "reload_rag",
    "clear_rag_documents",
    "unload_rag",
    "load_file_into_rag",
    "load_html_into_rag",
    "load_bytes_into_rag",
)


@runtime_checkable
class RAGService(Protocol):
    """The RAG operations invoked from outside the RAG subsystem.

    Implemented today by ``RAGMixin`` (via ``LLMModelManager``); the
    method signatures below mirror the mixin's current ones. Once a caller
    depends on this protocol rather than the manager, the implementation can
    move out of the LLM manager without a caller-visible change.
    """

    def search(self, query: str, k: int = 3) -> Sequence[Any]:
        """Return up to ``k`` retrieved document chunks for ``query``."""
        ...

    def ensure_indexed_files(self, file_paths: Sequence[str]) -> bool:
        """Index ``file_paths`` if not already present; False on failure."""
        ...

    def index_all_documents(self) -> bool:
        """Index every active document; False on failure."""
        ...

    def reload_rag(self) -> None:
        """Reset RAG caches/index state without unloading embeddings."""
        ...

    def clear_rag_documents(self) -> None:
        """Drop the active document set without unloading embeddings."""
        ...

    def unload_rag(self) -> None:
        """Unload the RAG runtime, including the embedding model."""
        ...

    def load_file_into_rag(self, file_path: str) -> None:
        """Load one file on disk into the RAG index."""
        ...

    def load_html_into_rag(
        self, html_content: str, source_name: str = "web_content"
    ) -> None:
        """Load one HTML string into the RAG index."""
        ...

    def load_bytes_into_rag(
        self,
        content_bytes: bytes,
        source_name: str,
        file_ext: str = ".epub",
    ) -> None:
        """Load raw document bytes into the RAG index via a temp file."""
        ...
