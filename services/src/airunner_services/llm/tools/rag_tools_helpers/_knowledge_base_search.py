"""Knowledge-base search helpers for RAG tools."""

import os
from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._shared import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
)


def get_active_documents(session: Any, document_model: Any) -> list[Any]:
    """Return active document records for one DB session."""
    return session.query(document_model).filter_by(active=True).all()


def get_candidate_directories(
    api: Any,
    path_settings_model: Any,
    logger: Any,
) -> list[str]:
    """Return candidate knowledge-base directories from configured paths."""
    settings = getattr(api, "path_settings", None)
    if settings is None:
        settings = path_settings_model.objects.first()
    logger.info("PathSettings: %s", settings)
    if not settings:
        return []
    return [
        settings.documents_path,
        settings.ebook_path,
        settings.webpages_path,
        os.path.join(settings.base_path, "knowledge_base"),
    ]


def discover_supported_files(
    directories: list[str],
    logger: Any,
) -> list[str]:
    """Return supported document paths found under the given directories."""
    found_files: list[str] = []
    logger.info("Candidate dirs for KB discovery: %s", directories)
    for directory in directories:
        if not directory:
            logger.debug("Skipping empty candidate dir")
            continue
        directory = os.path.expanduser(directory)
        if not os.path.exists(directory):
            logger.info("KB discovery dir not found: %s", directory)
            continue
        logger.info("Scanning KB dir for documents: %s", directory)
        file_count = 0
        for root, _, files in os.walk(directory):
            for file_name in files:
                extension = os.path.splitext(file_name)[1].lower()
                if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
                    continue
                file_count += 1
                found_files.append(os.path.join(root, file_name))
        logger.info("Found %s files in %s", file_count, directory)
    return found_files


def emit_discovery_signal(api: Any, signal_code: Any, file_path: str) -> None:
    """Emit one discovery signal when the API supports it."""
    if hasattr(api, "emit_signal"):
        api.emit_signal(
            signal_code.DOCUMENT_COLLECTION_CHANGED,
            {"path": file_path, "action": "discovered"},
        )


def upsert_discovered_documents(
    file_paths: list[str],
    *,
    api: Any,
    document_model: Any,
    signal_code: Any,
    logger: Any,
) -> None:
    """Create missing document records for newly discovered files."""
    logger.debug(
        "Found %s candidate files during discovery",
        len(file_paths),
    )
    for file_path in file_paths:
        exists = document_model.objects.filter_by(path=file_path)
        if exists and len(exists) > 0:
            logger.debug("Document already exists: %s", file_path)
            continue
        logger.info("Creating Document record for: %s", file_path)
        document_model.objects.create(
            path=file_path,
            active=True,
            indexed=False,
        )
        emit_discovery_signal(api, signal_code, file_path)


def find_repo_fallback_directories(module_file: str, logger: Any) -> list[str]:
    """Return repo fallback directories when a bundled booksite exists."""
    candidate = os.path.abspath(
        os.path.join(
            os.path.dirname(module_file),
            "..",
            "..",
            "..",
            "..",
            "..",
        )
    )
    while True:
        if os.path.exists(os.path.join(candidate, "booksite")):
            logger.debug("Repo fallback candidate root: %s", candidate)
            return [
                os.path.join(
                    candidate,
                    "booksite",
                    "text",
                    "other",
                    "documents",
                ),
                os.path.join(
                    candidate,
                    "booksite",
                    "text",
                    "other",
                    "ebooks",
                ),
                os.path.join(
                    candidate,
                    "booksite",
                    "text",
                    "other",
                    "webpages",
                ),
            ]
        parent = os.path.abspath(os.path.join(candidate, os.pardir))
        if parent == candidate:
            return []
        candidate = parent


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
            docs = get_active_documents(session, document_model)
            found_files: list[str] = []

            if not docs and api:
                logger.info(
                    "No docs in DB, attempting discovery. api=%s",
                    type(api).__name__,
                )
                try:
                    candidate_dirs = get_candidate_directories(
                        api,
                        path_settings_model,
                        logger,
                    )
                    found_files = discover_supported_files(candidate_dirs, logger)
                    upsert_discovered_documents(
                        found_files,
                        api=api,
                        document_model=document_model,
                        signal_code=signal_code,
                        logger=logger,
                    )
                    docs = get_active_documents(session, document_model)
                    logger.info(
                        "After discovery, DB now has %s active document records",
                        len(docs),
                    )
                except Exception as error:
                    logger.error(
                        "Disk discovery failed: %s",
                        error,
                        exc_info=True,
                    )

            if not docs and not found_files:
                try:
                    fallback_dirs = find_repo_fallback_directories(
                        module_file,
                        logger,
                    )
                    found_files = discover_supported_files(fallback_dirs, logger)
                    upsert_discovered_documents(
                        found_files,
                        api=api,
                        document_model=document_model,
                        signal_code=signal_code,
                        logger=logger,
                    )
                    if found_files:
                        docs = get_active_documents(session, document_model)
                except Exception as error:
                    logger.warning(
                        "Fallback repo discovery failed: %s",
                        error,
                    )

            if not docs:
                logger.info(
                    "[KB SEARCH] No docs found after all discovery attempts. "
                    "Returning error message."
                )
                return (
                    "No documents found in knowledge base. "
                    "⚠️ Try search_web() to search the internet instead, "
                    "then use record_knowledge() to save any useful facts."
                )

            top_docs = score_documents(docs, query)[:k]
            if not top_docs:
                try:
                    top_docs = retry_scoring_after_indexing(
                        docs,
                        query=query,
                        api=api,
                        session=session,
                        document_model=document_model,
                        logger=logger,
                    )[:k]
                except Exception as error:
                    logger.warning(
                        "On-demand indexing and retry failed: %s",
                        error,
                    )
                if not top_docs:
                    return (
                        "No documents found matching "
                        f"'{query}' in the knowledge base. "
                        f"⚠️ Try search_web('{query}') to search the internet "
                        "instead, then use record_knowledge() to save any "
                        "useful facts you find."
                    )

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