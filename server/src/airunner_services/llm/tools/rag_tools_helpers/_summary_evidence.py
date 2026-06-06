"""Summary-evidence builders for RAG tools."""

from types import SimpleNamespace
from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._document_access import (
    get_active_document_entries,
    get_single_active_document_path,
)
from airunner_services.llm.tools.rag_tools_helpers._document_splitting import (
    build_section_summary_units,
    build_summary_evidence_text,
    select_evenly_spaced_items,
    split_document_paragraphs,
    split_document_sections,
)
from airunner_services.llm.tools.rag_tools_helpers._premise_scoring import (
    build_premise_evidence_documents,
)
from airunner_services.llm.tools.rag_tools_helpers._shared import (
    SUMMARY_EVIDENCE_LIMIT,
)


def request_document_summary_focus(rag_manager: Any) -> str | None:
    """Return the request-scoped document summary subtype when available."""
    llm_request = getattr(rag_manager, "llm_request", None)
    request_plan = getattr(llm_request, "request_plan", None)
    focus = getattr(request_plan, "document_summary_focus", None)
    if isinstance(focus, str) and focus.strip():
        return focus.strip()
    focus = getattr(llm_request, "document_summary_focus", None)
    if isinstance(focus, str) and focus.strip():
        return focus.strip()
    return None


def request_document_query_intent(rag_manager: Any) -> str | None:
    """Return the request-scoped document intent when available."""
    llm_request = getattr(rag_manager, "llm_request", None)
    request_plan = getattr(llm_request, "request_plan", None)
    intent = getattr(request_plan, "document_query_intent", None)
    if isinstance(intent, str) and intent.strip():
        return intent.strip()
    intent = getattr(llm_request, "document_query_intent", None)
    if isinstance(intent, str) and intent.strip():
        return intent.strip()
    return None


def request_rewritten_query(rag_manager: Any) -> str | None:
    """Return the request-scoped rewritten query when available."""
    llm_request = getattr(rag_manager, "llm_request", None)
    rewritten_query = getattr(llm_request, "rewritten_prompt", None)
    if isinstance(rewritten_query, str) and rewritten_query.strip():
        return rewritten_query.strip()
    return None


def build_summary_evidence_documents(
    rag_manager: Any,
    metadata: dict[str, Any],
    text: str,
    *,
    query: str = "",
    summary_focus: str | None = None,
) -> list[Any]:
    """Build distributed summary evidence from one document text."""
    if summary_focus == "premise":
        builder = getattr(
            rag_manager,
            "build_structured_premise_evidence_documents",
            None,
        )
        if callable(builder):
            premise_documents = builder(
                metadata=metadata,
                query=query,
                text=text,
            )
            if premise_documents:
                return premise_documents
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

    return build_summary_evidence_documents(
        rag_manager,
        entries[0],
        text,
        query=query,
        summary_focus=request_document_summary_focus(rag_manager),
    )


__all__ = [
    "build_single_document_summary_results",
    "build_summary_evidence_documents",
    "request_document_query_intent",
    "request_document_summary_focus",
]
