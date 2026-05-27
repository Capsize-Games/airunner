"""Knowledge-base search helpers for RAG tools."""

import os
from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._knowledge_base_discovery import (
    get_active_documents,
    load_documents_with_discovery,
)


def score_documents(docs: list[Any], query: str) -> list[tuple[int, Any]]:
    """Return scored document matches using path and filename terms."""
    query_terms = query.lower().split()
    scored_docs = []
    for doc in docs:
        path_lower = doc.path.lower()
        filename = os.path.basename(path_lower)
        score = 0
        for term in query_terms:
            if term in filename:
                score += 10
            elif term in path_lower:
                score += 5
        if score > 0:
            scored_docs.append((score, doc))
    scored_docs.sort(reverse=True, key=lambda item: item[0])
    return scored_docs


def retry_scoring_after_indexing(
    docs: list[Any],
    *,
    query: str,
    api: Any,
    session: Any,
    document_model: Any,
    logger: Any,
) -> list[tuple[int, Any]]:
    """Retry filename scoring after indexing any unindexed documents."""
    rag_manager = getattr(api, "rag_manager", None)
    unindexed = [doc.path for doc in docs if not doc.indexed]
    if not unindexed or not hasattr(rag_manager, "ensure_indexed_files"):
        return []

    logger.info(
        "No filepath matches for query '%s'. Attempting to index %s "
        "documents and retry.",
        query,
        len(unindexed),
    )
    success = rag_manager.ensure_indexed_files(unindexed)
    if not success:
        return []
    return score_documents(get_active_documents(session, document_model), query)


def index_top_documents(top_docs: list[tuple[int, Any]], api: Any, logger: Any) -> int:
    """Index the matched top documents when the API exposes a RAG manager."""
    to_index_files = [doc.path for _, doc in top_docs if not doc.indexed]
    if not to_index_files or not api:
        return 0

    logger.debug(
        "Attempting to on-demand index %s files",
        len(to_index_files),
    )
    rag_manager = getattr(api, "rag_manager", None)
    if rag_manager is None or not hasattr(rag_manager, "ensure_indexed_files"):
        return 0

    try:
        success = rag_manager.ensure_indexed_files(to_index_files)
    except Exception as error:
        logger.warning("Failed to index files on demand: %s", error)
        return 0
    return len(to_index_files) if success else 0


def format_knowledge_base_results(
    top_docs: list[tuple[int, Any]],
    *,
    query: str,
    api: Any,
    logger: Any,
) -> str:
    """Return the formatted knowledge-base search response string."""
    result_parts = [
        f"Found {len(top_docs)} relevant document(s) for '{query}':\n"
    ]
    indexed_now_count = index_top_documents(top_docs, api, logger)
    indexed_paths = {
        doc.path for _, doc in top_docs if not doc.indexed
    } if indexed_now_count else set()

    for index, (_score, doc) in enumerate(top_docs, 1):
        filename = os.path.basename(doc.path)
        indexed_status = "indexed" if doc.indexed else "not indexed"
        if doc.path in indexed_paths:
            indexed_status = "indexed"
        result_parts.append(f"{index}. {filename} ({indexed_status})")
        result_parts.append(f"   Path: {doc.path}")

    result_parts.append(
        "\nTip: Use these document paths with rag_search to get detailed "
        "content."
    )
    if indexed_now_count > 0:
        result_parts.insert(
            0,
            "Automatically indexed "
            f"{indexed_now_count} document(s) and refreshed the KB.\n",
        )
    return "\n".join(result_parts)


    def _find_top_documents(
        docs: list[Any],
        *,
        query: str,
        k: int,
        api: Any,
        session: Any,
        document_model: Any,
        logger: Any,
    ) -> list[tuple[int, Any]]:
        """Return top-scored documents, retrying after indexing when needed."""
        top_docs = score_documents(docs, query)[:k]
        if top_docs:
            return top_docs
        try:
            return retry_scoring_after_indexing(
                docs,
                query=query,
                api=api,
                session=session,
                document_model=document_model,
                logger=logger,
            )[:k]
        except Exception as error:
            logger.warning("On-demand indexing and retry failed: %s", error)
            return []


    def _no_documents_message() -> str:
        """Return the message used when the KB has no documents."""
        return (
            "No documents found in knowledge base. "
            "⚠️ Try search_web() to search the internet instead, "
            "then use record_knowledge() to save any useful facts."
        )


    def _no_matches_message(query: str) -> str:
        """Return the message used when no KB documents match a query."""
        return (
            "No documents found matching "
            f"'{query}' in the knowledge base. "
            f"⚠️ Try search_web('{query}') to search the internet instead, "
            "then use record_knowledge() to save any useful facts you find."
        )


def search_knowledge_base_documents_impl(
    query: str,
    k: int,
    api: Any,
    *,
    session_scope: Any,
    document_model: Any,
    path_settings_model: Any,
    signal_code: Any,
    logger: Any,
    module_file: str,
) -> str:
    """Search active knowledge-base documents and discover missing ones."""
    try:
        with session_scope() as session:
            docs, _ = load_documents_with_discovery(
                api=api,
                session=session,
                document_model=document_model,
                path_settings_model=path_settings_model,
                signal_code=signal_code,
                logger=logger,
                module_file=module_file,
            )
            if not docs:
                logger.info(
                    "[KB SEARCH] No docs found after all discovery attempts. "
                    "Returning error message."
                )
                return _no_documents_message()

            top_docs = _find_top_documents(
                docs,
                query=query,
                k=k,
                api=api,
                session=session,
                document_model=document_model,
                logger=logger,
            )
            if not top_docs:
                return _no_matches_message(query)

            return format_knowledge_base_results(
                top_docs,
                query=query,
                api=api,
                logger=logger,
            )
    except Exception as error:
        logger.error("Error searching knowledge base: %s", error)
        return f"Error searching knowledge base: {str(error)}"


__all__ = ["search_knowledge_base_documents_impl"]