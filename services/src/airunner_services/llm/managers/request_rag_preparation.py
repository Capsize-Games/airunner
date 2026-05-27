"""Helpers for request-scoped RAG preparation."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from airunner_model.models.document import Document
from airunner_model.session import session_scope


def prepare_request_rag(
    manager: Any,
    llm_request: Any,
    selected_categories: Sequence[str],
) -> None:
    """Ensure request-provided or inferred RAG files are indexed."""
    if llm_request and getattr(llm_request, "rag_files", None):
        ensure_request_rag_files(manager, llm_request.rag_files)
        return

    try:
        if not llm_request or getattr(llm_request, "rag_files", None):
            return
        if "search" not in (selected_categories or []):
            return
        if not hasattr(manager, "ensure_indexed_files"):
            return

        candidates = _indexed_rag_candidates(limit=3)
        if not candidates:
            return

        llm_request.rag_files = candidates
        manager.logger.info(
            "Auto-attached %s indexed document(s) to rag_files for search: %s",
            len(candidates),
            candidates,
        )
        manager.ensure_indexed_files(candidates)
    except Exception:
        manager.logger.debug(
            "Auto attachment of RAG files failed, continuing without "
            "local RAG."
        )


def ensure_request_rag_files(manager: Any, rag_files: Any) -> None:
    """Load and index request-provided RAG files."""
    try:
        if hasattr(manager, "ensure_indexed_files"):
            manager.ensure_indexed_files(rag_files)
            return

        for document in rag_files:
            if isinstance(document, str):
                manager.load_file_into_rag(document)
                continue
            if isinstance(document, (bytes, bytearray)):
                manager.load_bytes_into_rag(document, source_name="upload")
                continue
            if isinstance(document, Mapping) and document.get("content"):
                load_rag_document_payload(manager, document)
    except Exception as exc:
        manager.logger.warning(
            "Error ensuring rag files are indexed: %s",
            exc,
        )


def load_rag_document_payload(manager: Any, document: Mapping[str, Any]) -> None:
    """Load one request-provided document payload into RAG."""
    file_type = str(document.get("file_type", "")).lower()
    content = document.get("content")
    source_name = document.get("source_name", "web_content")

    if file_type in [".epub", ".mobi", ".pdf"]:
        payload = content
        if not isinstance(payload, (bytes, bytearray)):
            payload = str(payload).encode("utf-8")
        manager.load_bytes_into_rag(
            payload,
            source_name=document.get("source_name", "upload"),
            file_ext=file_type,
        )
        return

    manager.load_html_into_rag(
        str(content),
        source_name=source_name,
    )


def _indexed_rag_candidates(limit: int) -> list[str]:
    """Return a small set of indexed documents for auto-attached search."""
    with session_scope() as session:
        documents = (
            session.query(Document)
            .filter_by(active=True, indexed=True)
            .all()
        )
    return [document.path for document in documents[:limit]]