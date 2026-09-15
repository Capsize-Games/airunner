"""Knowledge-base search workflow helpers for RAG tools."""

from collections.abc import Callable
from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._knowledge_base_discovery import (
    get_active_documents,
)


ScoredDocuments = list[tuple[int, Any]]
ScoreDocumentsFn = Callable[[list[Any], str], ScoredDocuments]


def retry_scoring_after_indexing(
    docs: list[Any], *, query: str, api: Any, session: Any,
    document_model: Any, logger: Any,
    score_documents_fn: ScoreDocumentsFn,
) -> ScoredDocuments:
    """Retry filename scoring after indexing any unindexed documents."""
    rag_manager = getattr(api, "rag_manager", None)
    unindexed = _unindexed_document_paths(docs)
    if not unindexed or not hasattr(rag_manager, "ensure_indexed_files"):
        return []
    logger.info(
        "No filepath matches for query '%s'. Attempting to index %s "
        "documents and retry.",
        query,
        len(unindexed),
    )
    if not _ensure_indexed_files(rag_manager, unindexed, logger):
        return []
    active_docs = get_active_documents(session, document_model)
    return score_documents_fn(active_docs, query)


def _unindexed_document_paths(docs: list[Any]) -> list[str]:
    """Return the paths for documents that still need indexing."""
    return [doc.path for doc in docs if not doc.indexed]


def _ensure_indexed_files(
    rag_manager: Any,
    file_paths: list[str],
    logger: Any,
) -> bool:
    """Index files through the RAG manager and normalize failures."""
    try:
        return bool(rag_manager.ensure_indexed_files(file_paths))
    except Exception as error:
        logger.warning("Failed to index files on demand: %s", error)
        return False


def find_top_documents(
    docs: list[Any], *, query: str, k: int, api: Any, session: Any,
    document_model: Any, logger: Any,
    score_documents_fn: ScoreDocumentsFn,
) -> ScoredDocuments:
    """Return top-scored documents, retrying after indexing when needed."""
    top_docs = score_documents_fn(docs, query)[:k]
    if top_docs:
        return top_docs
    try:
        return retry_scoring_after_indexing(
            docs, query=query, api=api, session=session,
            document_model=document_model, logger=logger,
            score_documents_fn=score_documents_fn,
        )[:k]
    except Exception as error:
        logger.warning("On-demand indexing and retry failed: %s", error)
        return []