"""Whole-document analysis helpers for RAG tools."""

from typing import Any

from langchain_core.messages.utils import count_tokens_approximately

from airunner_services.llm.tools.rag_tools_helpers._document_access import (
    get_active_document_entries,
    get_single_active_document_path,
)
from airunner_services.llm.tools.rag_tools_helpers._document_analysis_pipeline import (
    build_chunk_analyses,
    build_refined_document_synthesis,
    format_chunk_analyses,
    select_document_analysis_chunks,
)
from airunner_services.llm.tools.rag_tools_helpers._result_formatting import (
    document_label,
    format_summary_evidence_results,
)
from airunner_services.llm.tools.rag_tools_helpers._structured_document_analysis import (
    build_structured_document_analysis,
    request_structured_document_analysis_builder,
)
from airunner_services.llm.tools.rag_tools_helpers._summary_evidence import (
    build_summary_evidence_documents,
    request_document_summary_focus,
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
    rag_manager: Any,
    metadata: dict[str, Any],
    *,
    query: str,
    text: str,
    estimated_tokens: int,
    summary_focus: str | None = None,
    structured_analysis_builder: Any = None,
    logger: Any = None,
) -> str:
    """Return one chunked whole-document analysis context string."""
    analyses = build_chunk_analyses(
        query,
        text,
        summary_focus=summary_focus,
    )
    evidence = build_summary_evidence_documents(
        rag_manager,
        metadata,
        text,
        query=query,
        summary_focus=summary_focus,
    )
    coverage_chunks = select_document_analysis_chunks(
        text,
        summary_focus=summary_focus,
    )
    if not evidence and not coverage_chunks:
        return ""

    sections = [
        "Current document analysis:",
        f"Document: {document_label(metadata)}",
        "Analysis mode: chunked_document",
        "Analysis pipeline: distributed_evidence_bundle",
        f"Requested analysis: {query}",
        f"Estimated document tokens: {estimated_tokens}",
    ]
    coverage_outline = format_document_coverage(coverage_chunks)
    if coverage_outline:
        sections.extend(
            [
                "Document coverage:",
                coverage_outline,
            ]
        )
    refined_synthesis = build_refined_document_synthesis(analyses)
    structured_document_analysis = build_structured_document_analysis(
        structured_analysis_builder,
        metadata=metadata,
        query=query,
        analyses=analyses,
        evidence=evidence,
        coverage_chunks=coverage_chunks,
        refined_synthesis=refined_synthesis,
        summary_focus=summary_focus,
        logger=logger,
    )
    if refined_synthesis:
        sections.extend(
            [
                "Refined whole-document synthesis:",
                refined_synthesis,
            ]
        )
    if structured_document_analysis:
        sections.extend(
            [
                "Structured document analysis:",
                structured_document_analysis,
            ]
        )
    chunk_summaries = format_chunk_analyses(analyses)
    if chunk_summaries:
        sections.extend(
            [
                "Chunk summaries:",
                chunk_summaries,
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


def format_document_coverage(
    coverage_chunks: list[tuple[str, str]],
) -> str:
    """Return one numbered coverage outline for large-document analysis."""
    if not coverage_chunks:
        return ""

    lines = []
    for index, (title, _body) in enumerate(coverage_chunks, 1):
        cleaned_title = str(title or "").strip() or f"Document region {index}"
        lines.append(f"{index}. {cleaned_title}")
    return "\n".join(lines)


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
        rag_manager,
        entries[0],
        query=query,
        text=text,
        estimated_tokens=estimated_tokens,
        summary_focus=request_document_summary_focus(rag_manager),
        structured_analysis_builder=(
            request_structured_document_analysis_builder(rag_manager)
        ),
        logger=logger,
    )
    if chunked:
        return chunked
    return "The loaded document could not be prepared for whole-document analysis."


__all__ = ["analyze_loaded_document_impl"]