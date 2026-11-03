"""Scoped searches over the explicitly registered document catalog."""

import hashlib
import os
from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._knowledge_base_search_rendering import (
    format_knowledge_base_results,
    no_documents_message,
    no_matches_message,
)


def _document_id(path: str) -> str:
    """Match the persistent ID used by request RAG scope construction."""
    canonical = os.path.normpath(os.path.abspath(path))
    return hashlib.md5(canonical.encode()).hexdigest()


def score_documents(docs: list[Any], query: str) -> list[tuple[int, Any]]:
    """Rank catalog records by filename and path keyword matches."""
    query_terms = query.lower().split()
    scored = []
    for doc in docs:
        path = doc.path.lower()
        filename = os.path.basename(path)
        score = sum(
            10 if term in filename else 5 if term in path else 0
            for term in query_terms
        )
        if score:
            scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored


def search_knowledge_base_documents_impl(
    query: str,
    k: int,
    api: Any,
    *,
    session_scope: Any,
    document_model: Any,
    logger: Any,
    document_scope: tuple[str, ...] | None = None,
) -> str:
    """Search registered documents, honoring an explicit per-request scope.

    ``None`` retains the legacy standalone catalog search. An explicit tuple,
    including an empty tuple, restricts results to its document IDs. This
    function intentionally does no filesystem discovery or indexing.
    """
    del api  # Catalog search must not trigger implicit RAG-manager work.
    if document_scope is not None and not document_scope:
        return no_documents_message()
    try:
        with session_scope() as session:
            docs = session.query(document_model).filter_by(active=True).all()
        if document_scope is not None:
            allowed_ids = set(document_scope)
            docs = [doc for doc in docs if _document_id(doc.path) in allowed_ids]
        if not docs:
            return no_documents_message()
        top_docs = score_documents(docs, query)[: max(0, min(int(k), 50))]
        if not top_docs:
            return no_matches_message(query)
        return format_knowledge_base_results(top_docs, query=query)
    except Exception as error:
        logger.error("Error searching knowledge base: %s", error)
        return f"Error searching knowledge base: {error}"


__all__ = ["search_knowledge_base_documents_impl", "score_documents"]
