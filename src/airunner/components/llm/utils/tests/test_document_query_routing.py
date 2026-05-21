"""Unit tests for request-time document query routing."""

from airunner.components.llm.utils.document_query_routing import (
    route_document_query,
)


def test_route_document_query_routes_identity_to_inspection():
    """Identity questions should use the inspection tool."""
    route = route_document_query(
        "what is this document?",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "identity"
    assert route.force_tool == "inspect_loaded_documents"


def test_route_document_query_routes_inverted_identity_phrase():
    """'What document is this' should still use the inspection tool."""
    route = route_document_query(
        "what document is this?",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "identity"
    assert route.force_tool == "inspect_loaded_documents"


def test_route_document_query_routes_structure_to_inspection():
    """Structure questions should use the inspection tool."""
    route = route_document_query(
        "what chapters are in it?",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "structure"
    assert route.force_tool == "inspect_loaded_documents"


def test_route_document_query_routes_summary_to_retrieval():
    """Summary questions should use retrieval in document mode."""
    route = route_document_query(
        "summarize this document",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "summary"
    assert route.force_tool == "rag_search"


def test_route_document_query_defaults_to_retrieval_in_document_mode():
    """Other document questions should still use retrieval explicitly."""
    route = route_document_query(
        "what happened near the end?",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "retrieval"
    assert route.force_tool == "rag_search"


def test_route_document_query_treats_tell_me_more_as_summary():
    """Follow-up document prompts should stay on the summary path."""
    route = route_document_query(
        "tell me more about the book",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "summary"
    assert route.force_tool == "rag_search"