"""Formatting helpers for RAG tool responses."""

import os
from typing import Any


def document_label(metadata: dict[str, Any]) -> str:
    """Return one human-readable label for a retrieved document."""
    for key in ("file_name", "source", "file_path"):
        value = str(metadata.get(key, "") or "").strip()
        if not value:
            continue
        if key in {"source", "file_path"}:
            return os.path.basename(value) or value
        return value
    return "unknown"


def infer_filename_details(file_name: str) -> tuple[str | None, str | None]:
    """Infer one title and author hint from a filename when possible."""
    stem = os.path.splitext(os.path.basename(file_name))[0].strip()
    normalized_stem = stem.replace("_", " ").strip()
    if not normalized_stem or " - " not in normalized_stem:
        return None, None

    parts = [part.strip() for part in normalized_stem.split(" - ")]
    parts = [part for part in parts if part]
    if len(parts) < 2:
        return None, None

    title = " - ".join(parts[:-1]).strip() or None
    author = parts[-1].strip() or None
    return title, author


def format_document_summary(position: int, metadata: dict[str, Any]) -> str:
    """Format one matched-document summary for a RAG result."""
    label = document_label(metadata)
    lines = [f"Document {position}: {label}"]

    title_hint, author_hint = infer_filename_details(label)
    if title_hint:
        lines.append(f"Inferred title from filename: {title_hint}")
    if author_hint:
        lines.append(f"Inferred author from filename: {author_hint}")

    file_type = str(metadata.get("file_type", "") or "").strip()
    if file_type:
        lines.append(f"File type: {file_type}")

    file_path = str(
        metadata.get("file_path") or metadata.get("source") or ""
    ).strip()
    if file_path:
        lines.append(f"Stored path: {file_path}")

    return "\n".join(lines)


def format_excerpt(
    position: int,
    metadata: dict[str, Any],
    content: str,
    *,
    include_document_label: bool = True,
) -> str:
    """Format one retrieved excerpt with its document label."""
    excerpt = content[:500] if len(content) > 500 else content
    if not include_document_label:
        return excerpt
    label = document_label(metadata)
    return f"[Excerpt {position} from {label}]\n{excerpt}"


def format_rag_search_results(
    results: list[Any],
    *,
    include_excerpts: bool = True,
    include_document_summaries: bool = True,
    include_excerpt_labels: bool = True,
) -> str:
    """Return one user-facing RAG search result string."""
    document_summaries: list[str] = []
    excerpt_sections: list[str] = []
    seen_documents: set[str] = set()

    for index, doc in enumerate(results, 1):
        metadata = getattr(doc, "metadata", {}) or {}
        document_key = str(
            metadata.get("file_path")
            or metadata.get("file_name")
            or metadata.get("source")
            or f"result-{index}"
        )

        if include_document_summaries and document_key not in seen_documents:
            seen_documents.add(document_key)
            document_summaries.append(
                format_document_summary(len(document_summaries) + 1, metadata)
            )

        if include_excerpts:
            excerpt_sections.append(
                format_excerpt(
                    index,
                    metadata,
                    str(getattr(doc, "page_content", "") or ""),
                    include_document_label=include_excerpt_labels,
                )
            )

    sections = []
    if document_summaries:
        sections.append(
            "Matched documents:\n" + "\n\n".join(document_summaries)
        )
    if excerpt_sections:
        sections.append("Relevant excerpts:\n" + "\n\n".join(excerpt_sections))
    return "\n\n".join(sections)


def format_summary_evidence_results(results: list[Any]) -> str:
    """Return prompt-safe evidence for one active document summary."""
    excerpt_sections = []
    for index, doc in enumerate(results, 1):
        content = str(getattr(doc, "page_content", "") or "")
        excerpt_sections.append(f"[Excerpt {index}]\n{content}")

    sections = ["Current document: loaded document"]
    if excerpt_sections:
        sections.append("Relevant excerpts:\n" + "\n\n".join(excerpt_sections))
    return "\n\n".join(sections)


def format_loaded_document_results(entries: list[dict[str, Any]]) -> str:
    """Return one inspection summary for the currently loaded documents."""
    sections = [
        format_document_summary(index, metadata)
        for index, metadata in enumerate(entries, 1)
    ]
    return "Loaded documents:\n" + "\n\n".join(sections)


__all__ = [
    "document_label",
    "format_document_summary",
    "format_excerpt",
    "format_loaded_document_results",
    "format_rag_search_results",
    "format_summary_evidence_results",
    "infer_filename_details",
]
