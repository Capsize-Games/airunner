"""Helpers for document and ZIM resource-store access."""

from __future__ import annotations

from typing import Any

from airunner.daemon_client.resource_store import get_resource_store


def list_documents(*, filters: dict[str, Any] | None = None) -> list[Any]:
    """Return document records matching one optional filter."""
    return get_resource_store().query("Document", filters=filters)


def find_document_by_path(file_path: str) -> Any | None:
    """Return one document record for one exact file path."""
    return get_resource_store().first(
        "Document",
        filters={"path": file_path},
    )


def ensure_document_record(
    file_path: str,
    *,
    active: bool = False,
    indexed: bool = False,
    **extra: Any,
) -> Any:
    """Create one document record when it does not already exist."""
    existing = find_document_by_path(file_path)
    if existing is not None:
        return existing
    values = {
        "path": file_path,
        "active": active,
        "indexed": indexed,
        **extra,
    }
    return get_resource_store().create("Document", values)


def update_document(document_id: int, values: dict[str, Any]) -> Any:
    """Update one document record by id."""
    return get_resource_store().update("Document", document_id, values)


def delete_document(document_id: int) -> bool:
    """Delete one document record by id."""
    return get_resource_store().delete("Document", document_id)


def delete_documents_by_path(file_path: str) -> int:
    """Delete all document records for one exact file path."""
    deleted = 0
    for document in list_documents(filters={"path": file_path}):
        if delete_document(document.id):
            deleted += 1
    return deleted


def list_zim_files(*, filters: dict[str, Any] | None = None) -> list[Any]:
    """Return ZIM file records matching one optional filter."""
    return get_resource_store().query("ZimFile", filters=filters)


def find_zim_file_by_path(file_path: str) -> Any | None:
    """Return one ZIM file record for one exact file path."""
    return get_resource_store().first(
        "ZimFile",
        filters={"path": file_path},
    )


def create_zim_file(values: dict[str, Any]) -> Any:
    """Create one ZIM file record."""
    return get_resource_store().create("ZimFile", values)


def update_zim_file(zim_id: int, values: dict[str, Any]) -> Any:
    """Update one ZIM file record by id."""
    return get_resource_store().update("ZimFile", zim_id, values)


def delete_zim_file(zim_id: int) -> bool:
    """Delete one ZIM file record by id."""
    return get_resource_store().delete("ZimFile", zim_id)