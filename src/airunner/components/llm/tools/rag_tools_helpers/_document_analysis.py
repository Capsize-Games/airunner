"""Whole-document analysis helpers for RAG tools."""

from typing import Any

from langchain_core.messages.utils import count_tokens_approximately

from airunner.components.llm.tools.rag_tools_helpers._document_access import (
    get_active_document_entries,
    get_single_active_document_path,
)
from airunner.components.llm.tools.rag_tools_helpers._document_analysis_pipeline import (
    build_chunk_analyses,
    build_refined_document_synthesis,
    format_chunk_analyses,
)
from airunner.components.llm.tools.rag_tools_helpers._result_formatting import (
    document_label,
    format_summary_evidence_results,
)
from airunner.components.llm.tools.rag_tools_helpers._summary_evidence import (
    build_summary_evidence_documents,
)


FULL_DOCUMENT_ANALYSIS_TOKEN_LIMIT = 4000


def estimate_document_tokens(text: str) -> int:
    """Return one best-effort token estimate for document text."""
    if not text:
        return 0
    try:
        return count_tokens_approximately(text)
    except Exception:
        return (len(text) + 3) // 4


def request_document_capability(
    rag_manager: Any,
    file_path: str,
) -> dict[str, Any] | None:
    """Return request metadata for one attached document path."""
    llm_request = getattr(rag_manager, "llm_request", None)
    capabilities = getattr(llm_request, "attached_document_capabilities", [])
    for capability in capabilities or []:
        if str(capability.get("path", "") or "").strip() == file_path:
            return capability
    return None


def should_use_full_document_analysis(
    rag_manager: Any,
    file_path: str,
    estimated_tokens: int,
) -> bool:
    """Return whether the document should be analyzed as full text."""
    capability = request_document_capability(rag_manager, file_path)
    if capability and capability.get("fits_current_context"):
        return True

    llm_request = getattr(rag_manager, "llm_request", None)
    total_tokens = getattr(llm_request, "attached_document_total_tokens", 0)
    if total_tokens:
        return total_tokens <= FULL_DOCUMENT_ANALYSIS_TOKEN_LIMIT
    return estimated_tokens <= FULL_DOCUMENT_ANALYSIS_TOKEN_LIMIT


def build_full_document_analysis(
    metadata: dict[str, Any],
    *,
    query: str,
    text: str,
    estimated_tokens: int,
) -> str:
    """Return one full-document analysis context string."""
    label = document_label(metadata)
    sections = [
        "Current document analysis:",
        f"Document: {label}",
        "Analysis mode: full_document",
        f"Requested analysis: {query}",
        f"Estimated document tokens: {estimated_tokens}",
        "Full document text:",
        text,
    ]
    return "\n\n".join(sections)


def build_chunked_document_analysis(
    metadata: dict[str, Any],
    *,
    query: str,
    text: str,
    estimated_tokens: int,
) -> str:
    """Return one chunked whole-document analysis context string."""
    evidence = build_summary_evidence_documents(metadata, text, query=query)
    chunk_analyses = build_chunk_analyses(query, text)
    refined_synthesis = build_refined_document_synthesis(chunk_analyses)
    if not evidence and not chunk_analyses:
        return ""

    sections = [
        "Current document analysis:",
        f"Document: {document_label(metadata)}",
        "Analysis mode: chunked_document",
        "Analysis pipeline: deterministic_map_reduce",
        f"Requested analysis: {query}",
        f"Estimated document tokens: {estimated_tokens}",
    ]
    if refined_synthesis:
        sections.extend(
            [
                "Refined whole-document synthesis:",
                refined_synthesis,
            ]
        )
    if chunk_analyses:
        sections.extend(
            [
                "Chunk summaries:",
                format_chunk_analyses(chunk_analyses),
            ]
        )
    if evidence:
        sections.extend(
            [
                "Supporting evidence:",
                format_summary_evidence_results(evidence),
            ]
        )
    return "\n\n".join(sections)


def analyze_loaded_document_impl(
    rag_manager: Any,
    *,
    query: str,
    extract_text: Any,
    resolve_existing_file: Any,
    path_policy_error: type[Exception],
    logger: Any,
) -> str:
    """Return whole-document analysis context for one loaded document."""
    file_path = get_single_active_document_path(rag_manager)
    if not file_path:
        return (
            "Whole-document analysis requires exactly one loaded document. "
            "Load one document before using analyze_loaded_document."
        )

    try:
        resolved_path = resolve_existing_file(file_path, label="Document path")
    except path_policy_error as error:
        logger.warning("Skipping document analysis extraction: %s", error)
        return "The loaded document could not be opened for analysis."

    text = extract_text(resolved_path) or ""
    if not text.strip():
        return "The loaded document did not yield any readable text."

    entries = get_active_document_entries(rag_manager)
    if not entries:
        return "No documents are currently loaded into memory."

    estimated_tokens = estimate_document_tokens(text)
    if should_use_full_document_analysis(
        rag_manager,
        resolved_path,
        estimated_tokens,
    ):
        return build_full_document_analysis(
            entries[0],
            query=query,
            text=text,
            estimated_tokens=estimated_tokens,
        )

    chunked = build_chunked_document_analysis(
        entries[0],
        query=query,
        text=text,
        estimated_tokens=estimated_tokens,
    )
    if chunked:
        return chunked
    return "The loaded document could not be prepared for whole-document analysis."


__all__ = ["analyze_loaded_document_impl"]