"""Unit tests for RequestHandlingMixin RAG preparation."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.llm.managers.mixins.request_handling_mixin import (
    RequestHandlingMixin,
)
from airunner.enums import LLMActionType


class _DummyRequestHandlingMixin(RequestHandlingMixin):
    def __init__(self):
        self.logger = Mock()
        self.ensure_indexed_files = Mock(return_value=False)
        self._apply_tool_filter = Mock()
        self.get_tool_planner_system_prompt = Mock(
            return_value="planner prompt"
        )
        self.get_system_prompt_with_context = Mock(
            return_value="final chat prompt"
        )


def test_prepare_request_rag_returns_retry_error_for_embedding_download():
    """Attached-doc requests should pause until embeddings finish."""
    mixin = _DummyRequestHandlingMixin()
    mixin._rag_retry_after_download = True
    mixin._last_rag_index_error = "Embedding model download in progress."
    llm_request = SimpleNamespace(rag_files=["/tmp/doc.pdf"])

    result = mixin._prepare_request_rag({}, llm_request, ["rag"])

    mixin.ensure_indexed_files.assert_called_once_with(["/tmp/doc.pdf"])
    assert result == {
        "response": (
            "Error: the embedding model required for document search is "
            "still downloading. AIRunner will retry your request "
            "automatically when the download finishes."
        ),
        "error": "Embedding model download in progress.",
        "retry_after_download": True,
    }


def test_prepare_request_tooling_forces_document_inspection_tool():
    """Document identity questions should bypass model tool selection."""
    mixin = _DummyRequestHandlingMixin()
    llm_request = SimpleNamespace(
        tool_categories=["RAG", "SEARCH"],
        force_tool=None,
        system_prompt=None,
    )
    data = {
        "request_data": {
            "prompt": "what is this document?",
            "action": LLMActionType.PERFORM_RAG_SEARCH,
        }
    }

    result = mixin._prepare_request_tooling(data, llm_request)

    assert result[0] is True
    assert result[1] == ["RAG", "SEARCH"]
    assert llm_request.force_tool == "inspect_loaded_documents"
    assert llm_request.document_query_intent == "identity"
    assert llm_request.document_primary_tool == "inspect_loaded_documents"
    assert llm_request.document_answer_mode == "deterministic"
    assert mixin._current_document_query_route.intent == "identity"
    mixin._apply_tool_filter.assert_called_once_with(
        ["RAG", "SEARCH"],
        action=LLMActionType.PERFORM_RAG_SEARCH,
        force_tool="inspect_loaded_documents",
    )


def test_prepare_request_tooling_routes_inverted_identity_phrase():
    """The common inverted identity phrase should still force inspection."""
    mixin = _DummyRequestHandlingMixin()
    llm_request = SimpleNamespace(
        tool_categories=["RAG", "SEARCH"],
        force_tool=None,
        system_prompt=None,
    )
    data = {
        "request_data": {
            "prompt": "what document is this?",
            "action": LLMActionType.PERFORM_RAG_SEARCH,
        }
    }

    mixin._prepare_request_tooling(data, llm_request)

    assert llm_request.force_tool == "inspect_loaded_documents"
    assert llm_request.document_query_intent == "identity"
    assert llm_request.document_primary_tool == "inspect_loaded_documents"
    assert llm_request.document_answer_mode == "deterministic"
    assert mixin._current_document_query_route.intent == "identity"


def test_prepare_request_tooling_forces_document_retrieval_tool():
    """Document summaries should use retrieval without model tool planning."""
    mixin = _DummyRequestHandlingMixin()
    llm_request = SimpleNamespace(
        tool_categories=["RAG", "SEARCH"],
        force_tool=None,
        system_prompt=None,
    )
    data = {
        "request_data": {
            "prompt": "summarize this document",
            "action": LLMActionType.PERFORM_RAG_SEARCH,
        }
    }

    mixin._prepare_request_tooling(data, llm_request)

    assert llm_request.force_tool == "rag_search"
    assert llm_request.document_query_intent == "summary"
    assert llm_request.document_primary_tool == "rag_search"
    assert llm_request.document_answer_mode == "synthesized"
    assert mixin._current_document_query_route.intent == "summary"


def test_prepare_request_tooling_treats_attached_docs_as_document_mode():
    """Attached documents should enable document routing even in chat mode."""
    mixin = _DummyRequestHandlingMixin()
    llm_request = SimpleNamespace(
        tool_categories=["rag"],
        force_tool=None,
        system_prompt=None,
        rag_files=["/tmp/doc.pdf"],
    )
    data = {
        "request_data": {
            "prompt": "what chapters are in it?",
            "action": LLMActionType.CHAT,
        }
    }

    mixin._prepare_request_tooling(data, llm_request)

    assert llm_request.force_tool == "inspect_loaded_documents"
    assert llm_request.document_query_intent == "structure"
    assert llm_request.document_primary_tool == "inspect_loaded_documents"
    assert llm_request.document_answer_mode == "deterministic"
    assert mixin._current_document_query_route.intent == "structure"
    mixin._apply_tool_filter.assert_called_once_with(
        ["rag"],
        action=LLMActionType.CHAT,
        force_tool="inspect_loaded_documents",
    )


def test_prepare_request_tooling_overrides_stale_rag_search_force_tool():
    """Backend routing should correct generic rag_search forcing for identity queries."""
    mixin = _DummyRequestHandlingMixin()
    llm_request = SimpleNamespace(
        tool_categories=["rag"],
        force_tool="rag_search",
        system_prompt=None,
        rag_files=["/tmp/doc.pdf"],
    )
    data = {
        "request_data": {
            "prompt": "what is this document?",
            "action": LLMActionType.CHAT,
        }
    }

    mixin._prepare_request_tooling(data, llm_request)

    assert llm_request.force_tool == "inspect_loaded_documents"
    assert llm_request.document_query_intent == "identity"
    assert llm_request.document_primary_tool == "inspect_loaded_documents"
    assert llm_request.document_answer_mode == "deterministic"
    assert mixin._current_document_query_route.intent == "identity"


def test_prepare_request_tooling_routes_document_transform_task():
    """Formatting-heavy document tasks should stay on synthesized retrieval."""
    mixin = _DummyRequestHandlingMixin()
    llm_request = SimpleNamespace(
        tool_categories=["rag"],
        force_tool=None,
        system_prompt=None,
        rag_files=["/tmp/doc.pdf"],
    )
    data = {
        "request_data": {
            "prompt": "summarize the lab results in a table",
            "action": LLMActionType.CHAT,
        }
    }

    mixin._prepare_request_tooling(data, llm_request)

    assert llm_request.force_tool == "rag_search"
    assert llm_request.document_query_intent == "transform"
    assert llm_request.document_primary_tool == "rag_search"
    assert llm_request.document_answer_mode == "synthesized"
    assert mixin._current_document_query_route.intent == "transform"


def test_prepare_request_tooling_keeps_route_hints_in_planner_mode():
    """Planner mode should keep document hints without forcing the tool."""
    mixin = _DummyRequestHandlingMixin()
    llm_request = SimpleNamespace(
        tool_categories=["rag"],
        force_tool=None,
        system_prompt=None,
        rag_files=["/tmp/doc.pdf"],
        planner_mode="select_tools",
    )
    data = {
        "request_data": {
            "prompt": "what chapters are in it?",
            "action": LLMActionType.CHAT,
        }
    }

    mixin._prepare_request_tooling(data, llm_request)

    assert llm_request.force_tool is None
    assert llm_request.document_query_intent == "structure"
    assert llm_request.document_primary_tool == "inspect_loaded_documents"
    assert llm_request.document_answer_mode == "deterministic"
    assert llm_request.planner_tool_hints == ["inspect_loaded_documents"]
    assert mixin._current_document_query_route.intent == "structure"
    mixin._apply_tool_filter.assert_called_once_with(
        ["rag"],
        action=LLMActionType.CHAT,
        force_tool=None,
    )


def test_prepare_request_tooling_activates_planner_prompt_for_docs():
    """Attached-doc chats should enter through the planner prompt path."""
    mixin = _DummyRequestHandlingMixin()
    capabilities = [
        {
            "file_name": "notes.md",
            "estimated_tokens": 42,
            "text_available": True,
            "fits_current_context": True,
        }
    ]
    llm_request = SimpleNamespace(
        tool_categories=["rag"],
        force_tool=None,
        system_prompt=None,
        rag_files=["/tmp/doc.pdf"],
        planner_mode=None,
        final_system_prompt=None,
        attached_document_capabilities=capabilities,
        attached_document_total_tokens=42,
        attached_document_total_characters=128,
    )
    data = {
        "request_data": {
            "prompt": "what chapters are in it?",
            "action": LLMActionType.CHAT,
        }
    }

    result = mixin._prepare_request_tooling(data, llm_request)

    assert result[2] == "planner prompt"
    assert llm_request.planner_mode == "select_tools"
    assert llm_request.final_system_prompt == "final chat prompt"
    mixin.get_tool_planner_system_prompt.assert_called_once_with(
        LLMActionType.CHAT,
        tool_categories=["rag"],
        planner_tool_hints=["inspect_loaded_documents"],
        attached_document_capabilities=capabilities,
        attached_document_total_tokens=42,
        attached_document_total_characters=128,
    )
    mixin.get_system_prompt_with_context.assert_called_once_with(
        LLMActionType.CHAT,
        None,
        None,
    )


def test_prepare_request_tooling_prefers_document_analysis_hint_in_planner():
    """Planner hints should prefer whole-document analysis over RAG first."""
    mixin = _DummyRequestHandlingMixin()
    llm_request = SimpleNamespace(
        tool_categories=["rag"],
        force_tool=None,
        system_prompt=None,
        rag_files=["/tmp/doc.pdf"],
        planner_mode="select_tools",
    )
    data = {
        "request_data": {
            "prompt": "summarize this document",
            "action": LLMActionType.CHAT,
        }
    }

    mixin._prepare_request_tooling(data, llm_request)

    assert llm_request.planner_tool_hints == [
        "analyze_loaded_document",
        "rag_search",
    ]