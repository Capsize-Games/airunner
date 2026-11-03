"""Helpers for request-scoped RAG preparation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from airunner_services.database.models.document import Document
from airunner_services.database.session import session_scope
from airunner_services.runtimes.document_formats import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    UNSUPPORTED_BINARY_DOCUMENT_EXTENSIONS,
)


def prepare_request_rag(
    manager: Any,
    llm_request: Any,
    selected_categories: Sequence[str],
) -> tuple[str, ...]:
    """Ensure request-provided or inferred RAG files are indexed."""
    if llm_request and getattr(llm_request, "rag_files", None):
        return ensure_request_rag_files(manager, llm_request.rag_files)

    try:
        if not llm_request or getattr(llm_request, "rag_files", None):
            return ()
        if "search" not in (selected_categories or []):
            return ()
        if not hasattr(manager, "ensure_indexed_files"):
            return ()

        candidates = _indexed_rag_candidates(limit=3)
        if not candidates:
            return ()

        llm_request.rag_files = candidates
        manager.logger.info(
            "Auto-attached %s indexed document(s) to rag_files for search: %s",
            len(candidates),
            candidates,
        )
        manager.ensure_indexed_files(candidates)
        return ()
    except Exception:
        manager.logger.debug(
            "Auto attachment of RAG files failed, continuing without "
            "local RAG."
        )
        return ()


def ensure_request_rag_files(manager: Any, rag_files: Any) -> tuple[str, ...]:
    """Load every explicitly selected source or fail the request."""
    if not isinstance(rag_files, Sequence) or isinstance(
        rag_files, (str, bytes, bytearray)
    ):
        raise ValueError("Selected RAG documents are invalid")

    document_ids: list[str] = []
    for document in rag_files:
        if isinstance(document, str):
            _validate_selected_path(document)
            ensure_indexed = getattr(manager, "ensure_indexed_files", None)
            if callable(ensure_indexed):
                if ensure_indexed([document]) is False:
                    raise ValueError("Could not index a selected RAG document")
            else:
                manager.load_file_into_rag(document)
            continue

        if isinstance(document, (bytes, bytearray)):
            doc_id = manager.load_bytes_into_rag(
                document,
                source_name="upload",
                file_ext=".epub",
            )
            if not doc_id:
                raise ValueError("Could not index a selected RAG document")
            document_ids.append(str(doc_id))
            continue

        if isinstance(document, Mapping):
            path = document.get("path") or document.get("file_path")
            if path and not document.get("content"):
                if not isinstance(path, str):
                    raise ValueError("Selected RAG document path is invalid")
                _validate_selected_path(path)
                ensure_indexed = getattr(manager, "ensure_indexed_files", None)
                if callable(ensure_indexed):
                    if ensure_indexed([path]) is False:
                        raise ValueError(
                            "Could not index a selected RAG document"
                        )
                else:
                    manager.load_file_into_rag(path)
                continue

            if "content" not in document:
                raise ValueError("Selected RAG document payload is invalid")
            resolve_rag_payload_format(document)
            doc_id = load_rag_document_payload(manager, document)
            if not doc_id:
                raise ValueError("Could not index a selected RAG document")
            document_ids.append(str(doc_id))
            continue

        raise ValueError("Selected RAG document is invalid")

    return tuple(document_ids)


def _validate_selected_path(path: str) -> None:
    """Reject missing or unsupported explicitly selected local files."""
    if not os.path.isfile(path):
        raise ValueError("Selected RAG document does not exist")
    extension = Path(path).suffix.lower()
    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise ValueError(f"Unsupported document format: {extension or '<none>'}")


def resolve_rag_payload_format(document: Mapping[str, Any]) -> str:
    """Return one validated, normalized extension for a request payload."""
    file_type = str(document.get("file_type") or "").lower()
    if not file_type:
        source_name = (
            document.get("source_name")
            or document.get("path")
            or document.get("file_path")
            or ""
        )
        file_type = Path(str(source_name)).suffix.lower()
    if file_type and not file_type.startswith("."):
        file_type = f".{file_type}"
    if file_type in UNSUPPORTED_BINARY_DOCUMENT_EXTENSIONS:
        raise ValueError(f"Unsupported document format: {file_type}")
    if file_type == ".zim":
        raise ValueError("ZIM RAG documents must be selected by file path")
    if file_type and file_type not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise ValueError(f"Unsupported document format: {file_type}")
    return file_type


def load_rag_document_payload(manager: Any, document: Mapping[str, Any]) -> str | None:
    """Load one request-provided document payload into RAG."""
    file_type = resolve_rag_payload_format(document)
    content = document.get("content")
    source_name = document.get("source_name", "web_content")

    if file_type in [".epub", ".mobi", ".pdf"]:
        payload = content
        if not isinstance(payload, (bytes, bytearray)):
            payload = str(payload).encode("utf-8")
        return manager.load_bytes_into_rag(
            payload,
            source_name=document.get("source_name", "upload"),
            file_ext=file_type,
        )

    if file_type in {".html", ".htm"} and isinstance(
        content, (bytes, bytearray)
    ):
        content = bytes(content).decode("utf-8", errors="replace")
    elif file_type in {".md", ".txt"} and isinstance(
        content, (bytes, bytearray)
    ):
        content = bytes(content).decode("utf-8")

    result = manager.load_html_into_rag(
        str(content),
        source_name=source_name,
    )
    return str(result) if result else None


def _indexed_rag_candidates(limit: int) -> list[str]:
    """Return a small set of indexed documents for auto-attached search."""
    with session_scope() as session:
        documents = (
            session.query(Document)
            .filter_by(active=True, indexed=True)
            .all()
        )
    return [document.path for document in documents[:limit]]
