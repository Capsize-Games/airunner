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
    assert route.answer_mode == "deterministic"


def test_route_document_query_routes_inverted_identity_phrase():
    """'What document is this' should still use the inspection tool."""
    route = route_document_query(
        "what document is this?",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "identity"
    assert route.force_tool == "inspect_loaded_documents"
    assert route.answer_mode == "deterministic"


def test_route_document_query_routes_structure_to_inspection():
    """Structure questions should use the inspection tool."""
    route = route_document_query(
        "what chapters are in it?",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "structure"
    assert route.force_tool == "inspect_loaded_documents"
    assert route.answer_mode == "deterministic"


def test_route_document_query_routes_summary_to_retrieval():
    """Summary questions should use retrieval in document mode."""
    route = route_document_query(
        "summarize this document",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "summary"
    assert route.force_tool == "rag_search"
    assert route.answer_mode == "synthesized"
    assert route.summary_focus == "overview"


def test_route_document_query_marks_book_about_as_premise_summary():
    """Book-about document prompts should carry a premise-summary subtype."""
    route = route_document_query(
        "what is this book about?",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "summary"
    assert route.force_tool == "rag_search"
    assert route.answer_mode == "synthesized"
    assert route.summary_focus == "premise"


def test_route_document_query_marks_premise_theme_prompt_as_premise_summary():
    """Premise/theme prompts should carry the same summary subtype."""
    route = route_document_query(
        "what is the premise and theme of this book?",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "summary"
    assert route.summary_focus == "premise"


def test_route_document_query_marks_explain_premise_prompt_as_summary():
    """Broader premise phrasing should still enter the summary route."""
    route = route_document_query(
        "explain the premise of this book",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "summary"
    assert route.force_tool == "rag_search"
    assert route.answer_mode == "synthesized"
    assert route.summary_focus == "premise"


def test_route_document_query_defaults_to_retrieval_in_document_mode():
    """Other document questions should still use retrieval explicitly."""
    route = route_document_query(
        "what happened near the end?",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "retrieval"
    assert route.force_tool == "rag_search"
    assert route.answer_mode == "synthesized"


def test_route_document_query_treats_tell_me_more_as_summary():
    """Follow-up document prompts should stay on the summary path."""
    route = route_document_query(
        "tell me more about the book",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "summary"
    assert route.force_tool == "rag_search"
    assert route.answer_mode == "synthesized"


def test_route_document_query_routes_compare_task_to_retrieval():
    """Explicit comparison requests should use the synthesized document path."""
    route = route_document_query(
        "compare the lab results in this document",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "compare"
    assert route.force_tool == "rag_search"
    assert route.answer_mode == "synthesized"


def test_route_document_query_routes_extract_task_to_retrieval():
    """Extraction requests should use the synthesized document path."""
    route = route_document_query(
        "extract the key values from this pdf",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "extract"
    assert route.force_tool == "rag_search"
    assert route.answer_mode == "synthesized"


def test_route_document_query_routes_list_task_to_retrieval():
    """Enumeration requests should use the synthesized document path."""
    route = route_document_query(
        "list the medications in this document",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "list"
    assert route.force_tool == "rag_search"
    assert route.answer_mode == "synthesized"


def test_route_document_query_routes_transform_task_to_retrieval():
    """Formatting requests should use the synthesized document path."""
    route = route_document_query(
        "summarize the results in a table from this document",
        assume_document_mode=True,
    )

    assert route is not None
    assert route.intent == "transform"
    assert route.force_tool == "rag_search"
    assert route.answer_mode == "synthesized"