"""RAG and document search tools.

Tools for searching loaded documents (RAG), finding documents in knowledge
base, and saving new content to the knowledge base.
"""

import os
from typing import Annotated, Any

from airunner.components.data.session_manager import session_scope
from airunner.components.documents.data.models.document import Document
from airunner.components.llm.core.tool_registry import ToolCategory, tool
from airunner.components.llm.tools.rag_tools_helpers import (
    STANDARD_RETRIEVAL_K,
    SUMMARY_RETRIEVAL_K,
    analyze_loaded_document_impl,
    build_document_structure_result,
    build_single_document_summary_results,
    expand_query_with_active_document,
    format_loaded_document_results,
    format_rag_search_results,
    format_summary_evidence_results,
    get_active_document_entries,
    is_summary_query,
    search_knowledge_base_documents_impl,
)
from airunner.components.llm.utils.document_extraction import extract_text
from airunner.components.settings.data.path_settings import PathSettings
from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.application.log_hygiene import summarize_text
from airunner.utils.path_policy import PathPolicyError, resolve_existing_file

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


def _get_knowledge_base_settings(api: Any) -> Any:
    """Return path settings from the API or the persisted settings model."""
    settings = getattr(api, "path_settings", None)
    if settings is not None:
        return settings
    return PathSettings.objects.first()


def _sanitize_knowledge_base_category(category: str) -> str:
    """Return a filesystem-safe category name for knowledge-base writes."""
    sanitized = "".join(
        char for char in category if char.isalnum() or char in ("-", "_")
    ).strip()
    return sanitized or "general"


def _sanitize_knowledge_base_filename(title: str) -> str:
    """Return a filesystem-safe knowledge-base filename stem."""
    sanitized = "".join(
        char for char in title if char.isalnum() or char in (" ", "-", "_")
    ).strip()
    return sanitized.replace(" ", "_") + ".txt"


def _emit_knowledge_base_added(api: Any, file_path: str, title: str) -> None:
    """Emit one signal when the API supports knowledge-base updates."""
    if api and hasattr(api, "emit_signal"):
        api.emit_signal(
            SignalCode.RAG_DOCUMENT_ADDED,
            {"file_path": file_path, "title": title},
        )


@tool(
    name="inspect_loaded_documents",
    category=ToolCategory.RAG,
    description=(
        "Inspect the currently loaded documents and return metadata such as "
        "file name, inferred title, inferred author, file type, stored path, "
        "and extracted structure headings when available. Use this for "
        "questions about what the loaded document is or what chapters or "
        "sections it contains."
    ),
    return_direct=False,
    requires_api=True,
    keywords=[
        "document",
        "chapters",
        "sections",
        "title",
        "author",
        "outline",
        "contents",
    ],
    input_examples=[{}],
)
def inspect_loaded_documents(api: Any = None) -> str:
    """Return metadata and structure for the currently loaded documents."""
    rag_manager = api
    if not rag_manager:
        return (
            "TOOL UNAVAILABLE: No RAG manager available. "
            "This is an internal error."
        )

    entries = get_active_document_entries(rag_manager)
    if not entries:
        return (
            "No documents are currently loaded into memory. Load a document "
            "before inspecting it."
        )

    sections = [format_loaded_document_results(entries)]
    structure_result = build_document_structure_result(
        rag_manager,
        extract_text=extract_text,
        resolve_existing_file=resolve_existing_file,
        path_policy_error=PathPolicyError,
        logger=logger,
    )
    if structure_result:
        sections.append(structure_result)
    return "\n\n".join(sections)


@tool(
    name="analyze_loaded_document",
    category=ToolCategory.RAG,
    description=(
        "Prepare whole-document analysis context for the currently loaded "
        "document. Use this for summaries, premise/theme questions, and "
        "broad document transformations when you need more than local "
        "retrieval. This tool chooses either full-document or chunked "
        "context based on the request's document budget."
    ),
    return_direct=False,
    requires_api=True,
    keywords=[
        "document",
        "summary",
        "analyze",
        "whole document",
        "theme",
        "premise",
    ],
    input_examples=[{"query": "What is this book about?"}],
)
def analyze_loaded_document(
    query: Annotated[
        str,
        "Whole-document analysis request for the loaded document",
    ],
    api: Any = None,
) -> str:
    """Return whole-document analysis context for one loaded document."""
    if not api:
        return (
            "TOOL UNAVAILABLE: No RAG manager available. "
            "This is an internal error."
        )

    return analyze_loaded_document_impl(
        api,
        query=query,
        extract_text=extract_text,
        resolve_existing_file=resolve_existing_file,
        path_policy_error=PathPolicyError,
        logger=logger,
    )


@tool(
    name="rag_search",
    category=ToolCategory.RAG,
    description=(
        "Search through LOADED documents in memory for relevant information. "
        "IMPORTANT: Only works if documents have been loaded into memory "
        "first. If this fails because no documents are loaded, inform the "
        "user that documents need to be loaded first."
    ),
    return_direct=False,
    requires_api=True,
    keywords=["document", "search", "knowledge", "memory", "loaded"],
    input_examples=[
        {"query": "What is the main topic discussed in chapter 3?"},
        {"query": "Find information about machine learning algorithms"},
        {"query": "Summary of the introduction section"},
    ],
)
def rag_search(
    query: Annotated[
        str,
        "Search query for finding relevant document content",
    ],
    api: Any = None,
) -> str:
    """Search through loaded documents in memory for relevant information."""
    logger.info(
        "rag_search called (%s)",
        summarize_text(query, label="query"),
    )
    summary_query = is_summary_query(query)
    rag_manager = api

    logger.debug(
        "rag_manager available=%s has_search=%s",
        rag_manager is not None,
        hasattr(rag_manager, "search") if rag_manager else False,
    )

    if not rag_manager:
        error_msg = (
            "TOOL UNAVAILABLE: No RAG manager available. "
            "This is an internal error - RAG tools should receive the LLM "
            "model manager."
        )
        logger.warning(error_msg)
        return error_msg

    try:
        if summary_query:
            summary_results = build_single_document_summary_results(
                rag_manager,
                query=query,
                extract_text=extract_text,
                resolve_existing_file=resolve_existing_file,
                path_policy_error=PathPolicyError,
                logger=logger,
            )
            if summary_results:
                result_text = format_summary_evidence_results(summary_results)
                logger.info(
                    "Returning %s summary evidence excerpts built from full "
                    "document text",
                    len(summary_results),
                )
                return result_text

        effective_query = expand_query_with_active_document(query, rag_manager)
        if effective_query != query:
            logger.info(
                "Expanded RAG query with active document context (%s)",
                summarize_text(
                    effective_query,
                    label="effective_query",
                ),
            )

        results = rag_manager.search(
            effective_query,
            k=(
                SUMMARY_RETRIEVAL_K
                if summary_query
                else STANDARD_RETRIEVAL_K
            ),
        )
        logger.info(
            "rag_manager.search returned %s results",
            len(results) if results else 0,
        )

        if not results:
            message = (
                f"No relevant information found for '{query}' in loaded "
                "documents. The document may not contain information about "
                "this topic, or the search query may need to be rephrased."
            )
            logger.info(message)
            return message

        for index, doc in enumerate(results, 1):
            source = (getattr(doc, "metadata", {}) or {}).get(
                "source",
                "unknown",
            )
            logger.debug(
                "Result %s from source: %s, length: %s",
                index,
                source,
                len(getattr(doc, "page_content", "") or ""),
            )

        result_text = format_rag_search_results(
            results,
            include_excerpts=True,
            include_document_summaries=not summary_query,
            include_excerpt_labels=not summary_query,
        )
        logger.info(
            "Returning %s document excerpts, total length: %s",
            len(results),
            len(result_text),
        )
        return result_text
    except Exception as error:
        error_msg = f"Error searching documents: {str(error)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@tool(
    name="search_knowledge_base_documents",
    category=ToolCategory.SEARCH,
    description=(
        "Search across ALL knowledge base documents to find the most "
        "relevant ones. This is a broad search across document titles and "
        "paths - like a search engine for your entire knowledge base. Use "
        "this BEFORE rag_search to determine which documents should be "
        "loaded. If documents aren't indexed, this tool will automatically "
        "discover and index them."
    ),
    return_direct=False,
    requires_api=True,
)
def search_knowledge_base_documents(
    query: Annotated[
        str,
        "What topics/documents you're looking for (e.g., 'Python "
        "programming books')",
    ],
    k: Annotated[int, "Number of document paths to return"] = 10,
    api: Any = None,
) -> str:
    """Search across all knowledge-base documents to find relevant ones."""
    return search_knowledge_base_documents_impl(
        query,
        k,
        api,
        session_scope=session_scope,
        document_model=Document,
        path_settings_model=PathSettings,
        signal_code=SignalCode,
        logger=logger,
        module_file=__file__,
    )


@tool(
    name="save_to_knowledge_base",
    category=ToolCategory.RAG,
    description=(
        "Save content to the knowledge base for future RAG retrieval. "
        "This allows the agent to build its own knowledge base over time "
        "by saving important information for later reference."
    ),
    return_direct=False,
    requires_api=True,
)
def save_to_knowledge_base(
    content: Annotated[str, "Text content to save"],
    title: Annotated[str, "Title/identifier for this knowledge"],
    category: Annotated[
        str,
        "Category for organization (e.g., 'research', 'documentation')",
    ] = "general",
    api: Any = None,
) -> str:
    """Save content to the knowledge base for future RAG retrieval."""
    try:
        settings = _get_knowledge_base_settings(api)
        if settings is None or not getattr(settings, "base_path", None):
            return (
                "Error saving to knowledge base: No knowledge base path "
                "is configured."
            )

        safe_category = _sanitize_knowledge_base_category(category)
        base_path = os.path.expanduser(str(settings.base_path))
        kb_path = os.path.join(base_path, "knowledge_base", safe_category)
        os.makedirs(kb_path, exist_ok=True)

        file_path = os.path.join(
            kb_path,
            _sanitize_knowledge_base_filename(title),
        )
        with open(file_path, "w", encoding="utf-8") as file_handle:
            file_handle.write(f"Title: {title}\n")
            file_handle.write(f"Category: {safe_category}\n")
            file_handle.write("\n---\n\n")
            file_handle.write(content)

        _emit_knowledge_base_added(api, file_path, title)
        return f"Content saved to knowledge base: {title}"
    except Exception as error:
        return f"Error saving to knowledge base: {str(error)}"
