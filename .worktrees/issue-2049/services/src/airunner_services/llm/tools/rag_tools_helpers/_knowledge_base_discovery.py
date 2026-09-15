"""Document discovery helpers for knowledge-base search."""

import os
from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._shared import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
)


def get_active_documents(session: Any, document_model: Any) -> list[Any]:
    """Return active document records for one DB session."""
    return session.query(document_model).filter_by(active=True).all()


def load_documents_with_discovery(
    *,
    api: Any,
    session: Any,
    document_model: Any,
    path_settings_model: Any,
    signal_code: Any,
    logger: Any,
    module_file: str,
) -> tuple[list[Any], list[str]]:
    """Return active docs after configured and fallback discovery attempts."""
    docs = get_active_documents(session, document_model)
    found_files: list[str] = []
    if not docs and api:
        docs, found_files = _discover_configured_documents(
            api,
            session,
            document_model,
            path_settings_model,
            signal_code,
            logger,
        )
    if not docs and not found_files:
        docs, found_files = _discover_repo_documents(
            api,
            session,
            document_model,
            signal_code,
            logger,
            module_file,
        )
    return docs, found_files


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
        found_files.extend(_discover_directory_files(directory, logger))
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
    logger.debug("Found %s candidate files during discovery", len(file_paths))
    for file_path in file_paths:
        exists = document_model.objects.filter_by(path=file_path)
        if exists and len(exists) > 0:
            logger.debug("Document already exists: %s", file_path)
            continue
        logger.info("Creating Document record for: %s", file_path)
        document_model.objects.create(path=file_path, active=True, indexed=False)
        emit_discovery_signal(api, signal_code, file_path)


def find_repo_fallback_directories(module_file: str, logger: Any) -> list[str]:
    """Return repo fallback directories when a bundled booksite exists."""
    candidate = os.path.abspath(
        os.path.join(os.path.dirname(module_file), "..", "..", "..", "..", "..")
    )
    while True:
        booksite_dirs = _booksite_directories(candidate)
        if booksite_dirs is not None:
            logger.debug("Repo fallback candidate root: %s", candidate)
            return booksite_dirs
        parent = os.path.abspath(os.path.join(candidate, os.pardir))
        if parent == candidate:
            return []
        candidate = parent


def _discover_configured_documents(
    api: Any,
    session: Any,
    document_model: Any,
    path_settings_model: Any,
    signal_code: Any,
    logger: Any,
) -> tuple[list[Any], list[str]]:
    """Discover documents from configured knowledge-base directories."""
    logger.info("No docs in DB, attempting discovery. api=%s", type(api).__name__)
    try:
        candidate_dirs = get_candidate_directories(api, path_settings_model, logger)
        found_files = discover_supported_files(candidate_dirs, logger)
        upsert_discovered_documents(
            found_files,
            api=api,
            document_model=document_model,
            signal_code=signal_code,
            logger=logger,
        )
        docs = get_active_documents(session, document_model)
        logger.info("After discovery, DB now has %s active document records", len(docs))
        return docs, found_files
    except Exception as error:
        logger.error("Disk discovery failed: %s", error, exc_info=True)
        return [], []


def _discover_repo_documents(
    api: Any,
    session: Any,
    document_model: Any,
    signal_code: Any,
    logger: Any,
    module_file: str,
) -> tuple[list[Any], list[str]]:
    """Discover documents from repo fallback directories when available."""
    try:
        fallback_dirs = find_repo_fallback_directories(module_file, logger)
        found_files = discover_supported_files(fallback_dirs, logger)
        upsert_discovered_documents(
            found_files,
            api=api,
            document_model=document_model,
            signal_code=signal_code,
            logger=logger,
        )
        docs = get_active_documents(session, document_model) if found_files else []
        return docs, found_files
    except Exception as error:
        logger.warning("Fallback repo discovery failed: %s", error)
        return [], []


def _discover_directory_files(directory: str, logger: Any) -> list[str]:
    """Return supported files found under one expanded directory."""
    expanded = os.path.expanduser(directory)
    if not os.path.exists(expanded):
        logger.info("KB discovery dir not found: %s", expanded)
        return []
    logger.info("Scanning KB dir for documents: %s", expanded)
    found_files: list[str] = []
    file_count = 0
    for root, _, files in os.walk(expanded):
        for file_name in files:
            if os.path.splitext(file_name)[1].lower() not in SUPPORTED_DOCUMENT_EXTENSIONS:
                continue
            file_count += 1
            found_files.append(os.path.join(root, file_name))
    logger.info("Found %s files in %s", file_count, expanded)
    return found_files


def _booksite_directories(candidate: str) -> list[str] | None:
    """Return bundled booksite directories for a candidate repo root."""
    if not os.path.exists(os.path.join(candidate, "booksite")):
        return None
    return [
        os.path.join(candidate, "booksite", "text", "other", "documents"),
        os.path.join(candidate, "booksite", "text", "other", "ebooks"),
        os.path.join(candidate, "booksite", "text", "other", "webpages"),
    ]