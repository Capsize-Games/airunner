"""Active-document inspection and query-expansion helpers."""

import os
from os import PathLike
from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._document_splitting import (
    extract_document_structure_headings,
)


def coerce_active_values(values: Any) -> list[str]:
    """Return normalized string values from one manager accessor result."""
    if values is None:
        return []
    if isinstance(values, (str, PathLike)):
        values = [values]
    else:
        try:
            values = list(values)
        except TypeError:
            return []

    return [
        str(value).strip()
        for value in values
        if str(value or "").strip()
    ]


def get_single_active_document_path(rag_manager: Any) -> str | None:
    """Return the one active document path when exactly one is loaded."""
    get_paths = getattr(rag_manager, "_get_active_document_paths", None)
    if not callable(get_paths):
        return None

    active_paths = list(dict.fromkeys(coerce_active_values(get_paths())))
    if len(active_paths) != 1:
        return None
    return active_paths[0]


def get_active_document_names(rag_manager: Any) -> list[str]:
    """Return distinct active document names when the manager exposes them."""
    get_names = getattr(rag_manager, "_get_active_document_names", None)
    if not callable(get_names):
        return []
    return list(dict.fromkeys(coerce_active_values(get_names())))


def get_active_document_entries(rag_manager: Any) -> list[dict[str, Any]]:
    """Return active document metadata entries for inspection tools."""
    entries: list[dict[str, Any]] = []
    active_names = get_active_document_names(rag_manager)

    get_paths = getattr(rag_manager, "_get_active_document_paths", None)
    active_paths: list[str] = []
    if callable(get_paths):
        active_paths = list(dict.fromkeys(coerce_active_values(get_paths())))

    if active_paths:
        for index, path in enumerate(active_paths):
            name = (
                active_names[index]
                if index < len(active_names)
                else os.path.basename(path)
            )
            label = str(name or "").strip() or os.path.basename(path) or path
            entries.append(
                {
                    "source": path,
                    "file_name": label,
                    "file_type": os.path.splitext(label)[1],
                    "file_path": path,
                }
            )
        return entries

    for name in active_names:
        entries.append(
            {
                "source": name,
                "file_name": name,
                "file_type": os.path.splitext(name)[1],
                "file_path": "",
            }
        )
    return entries


def build_document_structure_result(
    rag_manager: Any,
    *,
    extract_text: Any,
    resolve_existing_file: Any,
    path_policy_error: type[Exception],
    logger: Any,
) -> str | None:
    """Return structure headings for one active document when available."""
    file_path = get_single_active_document_path(rag_manager)
    if not file_path:
        return None

    try:
        resolved_path = resolve_existing_file(file_path, label="Document path")
    except path_policy_error as error:
        logger.warning("Skipping structure extraction: %s", error)
        return None

    headings = extract_document_structure_headings(
        extract_text(resolved_path) or ""
    )
    if not headings:
        return None

    structure = "\n".join(
        f"{index}. {heading}"
        for index, heading in enumerate(headings, 1)
    )
    return "Document structure:\n" + structure


__all__ = [
    "build_document_structure_result",
    "get_active_document_entries",
    "get_single_active_document_path",
]