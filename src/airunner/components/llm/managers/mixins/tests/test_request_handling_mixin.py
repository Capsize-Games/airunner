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
    assert mixin._current_document_query_route.intent == "identity"
    mixin._apply_tool_filter.assert_called_once_with(
        ["RAG", "SEARCH"],
        action=LLMActionType.PERFORM_RAG_SEARCH,
        force_tool="inspect_loaded_documents",
    )


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
    assert mixin._current_document_query_route.intent == "summary"