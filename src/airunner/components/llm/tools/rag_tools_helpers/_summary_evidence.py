"""Summary-evidence builders for RAG tools."""

from types import SimpleNamespace
from typing import Any

from airunner.components.llm.tools.rag_tools_helpers._document_access import (
    get_active_document_entries,
    get_single_active_document_path,
)
from airunner.components.llm.tools.rag_tools_helpers._document_splitting import (
    build_section_summary_units,
    build_summary_evidence_text,
    select_evenly_spaced_items,
    split_document_paragraphs,
    split_document_sections,
)
from airunner.components.llm.tools.rag_tools_helpers._premise_scoring import (
    build_premise_evidence_documents,
)
from airunner.components.llm.tools.rag_tools_helpers._query_classification import (
    is_premise_summary_query,
)
from airunner.components.llm.tools.rag_tools_helpers._shared import (
    SUMMARY_EVIDENCE_LIMIT,
)


def build_summary_evidence_documents(
    metadata: dict[str, Any],
    text: str,
    *,
    query: str = "",
) -> list[Any]:
    """Build distributed summary evidence from one document text."""
    if is_premise_summary_query(query):
        premise_documents = build_premise_evidence_documents(metadata, text)
        if premise_documents:
            return premise_documents

    sections = split_document_sections(text)
    if sections:
        selected_sections = select_evenly_spaced_items(
            build_section_summary_units(sections),
            SUMMARY_EVIDENCE_LIMIT,
        )
        return [
            SimpleNamespace(
                metadata=dict(metadata),
                page_content=build_summary_evidence_text(title, body, index),
            )
            for index, (title, body) in enumerate(selected_sections, 1)
        ]

    paragraphs = split_document_paragraphs(text)
    if not paragraphs:
        return []
    selected_paragraphs = select_evenly_spaced_items(
        paragraphs,
        SUMMARY_EVIDENCE_LIMIT,
    )
    return [
        SimpleNamespace(
            metadata=dict(metadata),
            page_content=build_summary_evidence_text("", paragraph, index),
        )
        for index, paragraph in enumerate(selected_paragraphs, 1)
    ]


def build_single_document_summary_results(
    rag_manager: Any,
    *,
    query: str = "",
    extract_text: Any,
    resolve_existing_file: Any,
    path_policy_error: type[Exception],
    logger: Any,
) -> list[Any]:
    """Return document-wide summary evidence for one active document."""
    file_path = get_single_active_document_path(rag_manager)
    if not file_path:
        return []

    try:
        resolved_path = resolve_existing_file(file_path, label="Document path")
    except path_policy_error as error:
        logger.warning("Skipping summary evidence extraction: %s", error)
        return []

    text = extract_text(resolved_path) or ""
    if not text.strip():
        return []

    entries = get_active_document_entries(rag_manager)
    if not entries:
        return []

    return build_summary_evidence_documents(entries[0], text, query=query)


__all__ = [
    "build_single_document_summary_results",
    "build_summary_evidence_documents",
]