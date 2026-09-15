"""Knowledge-base search rendering helpers for RAG tools."""

import os
from typing import Any


def index_top_documents(
    top_docs: list[tuple[int, Any]],
    api: Any,
    logger: Any,
) -> int:
    """Index the matched top documents when the API exposes a RAG manager."""
    to_index_files = _unindexed_top_document_paths(top_docs)
    rag_manager = getattr(api, "rag_manager", None) if api else None
    if not to_index_files or rag_manager is None:
        return 0
    if not hasattr(rag_manager, "ensure_indexed_files"):
        return 0
    logger.debug("Attempting to on-demand index %s files", len(to_index_files))
    if not _ensure_indexed_files(rag_manager, to_index_files, logger):
        return 0
    return len(to_index_files)


def _unindexed_top_document_paths(
    top_docs: list[tuple[int, Any]],
) -> list[str]:
    """Return unindexed paths for the selected top documents."""
    return [doc.path for _, doc in top_docs if not doc.indexed]


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


def format_knowledge_base_results(
    top_docs: list[tuple[int, Any]],
    *,
    query: str,
    api: Any,
    logger: Any,
) -> str:
    """Return the formatted knowledge-base search response string."""
    indexed_now_count = index_top_documents(top_docs, api, logger)
    result_parts = _knowledge_base_result_header(top_docs, query)
    indexed_paths = _indexed_paths_after_refresh(top_docs, indexed_now_count)
    result_parts.extend(_formatted_document_entries(top_docs, indexed_paths))
    result_parts.append(_knowledge_base_tip())
    if indexed_now_count > 0:
        result_parts.insert(0, _indexed_documents_message(indexed_now_count))
    return "\n".join(result_parts)


def _knowledge_base_result_header(
    top_docs: list[tuple[int, Any]],
    query: str,
) -> list[str]:
    """Return the standard leading lines for KB search results."""
    return [f"Found {len(top_docs)} relevant document(s) for '{query}':\n"]


def _indexed_paths_after_refresh(
    top_docs: list[tuple[int, Any]],
    indexed_now_count: int,
) -> set[str]:
    """Return paths that were indexed during the current result format."""
    if not indexed_now_count:
        return set()
    return {doc.path for _, doc in top_docs if not doc.indexed}


def _formatted_document_entries(
    top_docs: list[tuple[int, Any]],
    indexed_paths: set[str],
) -> list[str]:
    """Return formatted document lines for knowledge-base results."""
    lines: list[str] = []
    for index, (_score, doc) in enumerate(top_docs, 1):
        lines.extend(_formatted_document_entry(index, doc, indexed_paths))
    return lines


def _formatted_document_entry(
    index: int,
    doc: Any,
    indexed_paths: set[str],
) -> list[str]:
    """Return one formatted document entry for KB search results."""
    filename = os.path.basename(doc.path)
    indexed_status = "indexed" if doc.indexed else "not indexed"
    if doc.path in indexed_paths:
        indexed_status = "indexed"
    return [
        f"{index}. {filename} ({indexed_status})",
        f"   Path: {doc.path}",
    ]


def _knowledge_base_tip() -> str:
    """Return the KB search follow-up tip appended to results."""
    return (
        "\nTip: Use these document paths with rag_search to get detailed "
        "content."
    )


def _indexed_documents_message(indexed_now_count: int) -> str:
    """Return the lead line announcing on-demand indexing."""
    return (
        "Automatically indexed "
        f"{indexed_now_count} document(s) and refreshed the KB.\n"
    )


def no_documents_message() -> str:
    """Return the message used when the KB has no documents."""
    return (
        "No documents found in knowledge base. "
        "⚠️ Try search_web() to search the internet instead, "
        "then use record_knowledge() to save any useful facts."
    )


def no_matches_message(query: str) -> str:
    """Return the message used when no KB documents match a query."""
    return (
        "No documents found matching "
        f"'{query}' in the knowledge base. "
        f"⚠️ Try search_web('{query}') to search the internet instead, "
        "then use record_knowledge() to save any useful facts you find."
    )