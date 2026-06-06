"""Knowledge-base search helpers for RAG tools."""

import os
from typing import Any

from airunner_services.llm.tools.rag_tools_helpers._knowledge_base_discovery import (
    load_documents_with_discovery,
)
from airunner_services.llm.tools.rag_tools_helpers._knowledge_base_search_rendering import (
    format_knowledge_base_results,
    no_documents_message,
    no_matches_message,
)
from airunner_services.llm.tools.rag_tools_helpers._knowledge_base_search_workflow import (
    find_top_documents,
)

SearchDocs = list[Any]


def score_documents(docs: list[Any], query: str) -> list[tuple[int, Any]]:
    """Return scored document matches using path and filename terms."""
    query_terms = query.lower().split()
    scored_docs = []
    for doc in docs:
        score = _score_document_terms(doc, query_terms)
        if score > 0:
            scored_docs.append((score, doc))
    scored_docs.sort(reverse=True, key=lambda item: item[0])
    return scored_docs


def _score_document_terms(doc: Any, query_terms: list[str]) -> int:
    """Return the filename/path term match score for one document."""
    path_lower = doc.path.lower()
    filename = os.path.basename(path_lower)
    score = 0
    for term in query_terms:
        if term in filename:
            score += 10
        elif term in path_lower:
            score += 5
    return score


def _load_discovered_documents(
    api: Any,
    *,
    session: Any,
    document_model: Any,
    path_settings_model: Any,
    signal_code: Any,
    logger: Any,
    module_file: str,
) -> list[Any]:
    """Load KB documents after running discovery for the active session."""
    docs, _ = load_documents_with_discovery(
        api=api,
        session=session,
        document_model=document_model,
        path_settings_model=path_settings_model,
        signal_code=signal_code,
        logger=logger,
        module_file=module_file,
    )
    return docs


def _search_result_from_docs(
    docs: SearchDocs,
    *,
    query: str,
    k: int,
    api: Any,
    session: Any,
    document_model: Any,
    logger: Any,
) -> str:
    """Return the KB search result for already-discovered documents."""
    if not docs:
        logger.info(
            "[KB SEARCH] No docs found after all discovery attempts. "
            "Returning error message."
        )
        return no_documents_message()

    top_docs = find_top_documents(
        docs,
        query=query,
        k=k,
        api=api,
        session=session,
        document_model=document_model,
        logger=logger,
        score_documents_fn=score_documents,
    )
    if not top_docs:
        return no_matches_message(query)
    return format_knowledge_base_results(
        top_docs, query=query, api=api, logger=logger
    )


def _search_knowledge_base_in_session(
    query: str,
    k: int,
    api: Any,
    *,
    session: Any,
    document_model: Any,
    path_settings_model: Any,
    signal_code: Any,
    logger: Any,
    module_file: str,
) -> str:
    """Run one KB search inside an already-open session."""
    docs = _load_discovered_documents(
        api,
        session=session,
        document_model=document_model,
        path_settings_model=path_settings_model,
        signal_code=signal_code,
        logger=logger,
        module_file=module_file,
    )
    return _search_result_from_docs(
        docs,
        query=query,
        k=k,
        api=api,
        session=session,
        document_model=document_model,
        logger=logger,
    )


def search_knowledge_base_documents_impl(
    query: str,
    k: int,
    api: Any,
    *,
    session_scope: Any,
    document_model: Any,
    path_settings_model: Any,
    signal_code: Any,
    logger: Any,
    module_file: str,
) -> str:
    """Search active knowledge-base documents and discover missing ones."""
    try:
        with session_scope() as session:
            return _search_knowledge_base_in_session(
                query=query,
                k=k,
                api=api,
                session=session,
                document_model=document_model,
                path_settings_model=path_settings_model,
                signal_code=signal_code,
                logger=logger,
                module_file=module_file,
            )
    except Exception as error:
        logger.error("Error searching knowledge base: %s", error)
        return f"Error searching knowledge base: {str(error)}"


__all__ = ["search_knowledge_base_documents_impl"]
