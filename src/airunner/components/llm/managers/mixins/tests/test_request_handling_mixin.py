"""Unit tests for RequestHandlingMixin RAG preparation."""

from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.llm.managers.mixins.tool_classification_mixin import (
    ToolClassificationMixin,
)
from airunner.components.llm.managers.mixins.request_handling_mixin import (
    RequestHandlingMixin,
)
from airunner.enums import LLMActionType


class _DummyRequestHandlingMixin(RequestHandlingMixin, ToolClassificationMixin):
    def __init__(self):
        self.logger = Mock()
        self.emit_signal = Mock()
        self.ensure_indexed_files = Mock(return_value=False)
        self._apply_tool_filter = Mock()
        self._preprocess_request = Mock(return_value=None)
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


def test_prepare_request_tooling_applies_preprocess_categories():
    """Request tooling should use the LLM preprocess result directly."""
    mixin = _DummyRequestHandlingMixin()
    mixin._preprocess_request.return_value = {
        "rewrite_needed": False,
        "rewritten_query": "tell me the current time",
        "tool_required": True,
        "tool_categories": ["system"],
        "primary_tool": "get_current_datetime",
        "planner_tool_hints": ["get_current_datetime"],
        "document_query_intent": None,
        "document_summary_focus": None,
        "document_answer_mode": None,
    }
    llm_request = SimpleNamespace(
        tool_categories=None,
        force_tool=None,
        system_prompt=None,
        rewritten_prompt=None,
        preprocessed_primary_tool=None,
    )
    data = {
        "request_data": {
            "prompt": "tell me the current time",
            "action": LLMActionType.CHAT,
        }
    }

    result = mixin._prepare_request_tooling(data, llm_request)

    assert result[0] is True
    assert result[1] == ["system"]
    assert llm_request.tool_categories == ["system"]
    assert llm_request.preprocessed_primary_tool == "get_current_datetime"
    assert llm_request.request_plan.primary_tool == "get_current_datetime"
    assert llm_request.request_plan.allowed_tool_names == [
        "get_current_datetime"
    ]
    assert llm_request.force_tool == "get_current_datetime"
    mixin._apply_tool_filter.assert_called_once_with(
        ["system"],
        action=LLMActionType.CHAT,
        force_tool="get_current_datetime",
        allowed_tool_names=None,
    )


def test_prepare_request_tooling_records_document_metadata_from_preprocess():
    """Primary document tools should be forced from the request plan."""
    mixin = _DummyRequestHandlingMixin()
    mixin._preprocess_request.return_value = {
        "rewrite_needed": False,
        "rewritten_query": "what chapters are in the attached document?",
        "tool_required": True,
        "tool_categories": ["rag"],
        "primary_tool": "inspect_loaded_documents",
        "planner_tool_hints": ["inspect_loaded_documents"],
        "document_query_intent": "structure",
        "document_summary_focus": None,
        "document_answer_mode": "deterministic",
    }
    llm_request = SimpleNamespace(
        tool_categories=None,
        force_tool=None,
        system_prompt=None,
        rewritten_prompt=None,
        preprocessed_primary_tool=None,
        rag_files=["/tmp/doc.pdf"],
        planner_mode=None,
        final_system_prompt=None,
    )
    data = {
        "request_data": {
            "prompt": "what chapters are in it?",
            "action": LLMActionType.CHAT,
        }
    }

    mixin._prepare_request_tooling(data, llm_request)

    assert llm_request.force_tool == "inspect_loaded_documents"
    assert llm_request.planner_mode is None
    assert llm_request.document_query_intent == "structure"
    assert llm_request.document_primary_tool == "inspect_loaded_documents"
    assert llm_request.document_answer_mode == "deterministic"
    assert llm_request.planner_tool_hints == ["inspect_loaded_documents"]
    assert llm_request.request_plan.document_query_intent == "structure"
    assert llm_request.request_plan.planner_mode is None
    assert llm_request.request_plan.allowed_tool_names == [
        "inspect_loaded_documents"
    ]
    assert mixin._current_document_query_route.intent == "structure"


def test_prepare_request_tooling_uses_planner_prompt_for_attached_docs():
    """Attached documents should still activate the planner prompt path."""
    mixin = _DummyRequestHandlingMixin()
    capabilities = [
        {
            "file_name": "notes.md",
            "estimated_tokens": 42,
            "text_available": True,
            "fits_current_context": True,
        }
    ]
    mixin._preprocess_request.return_value = {
        "rewrite_needed": False,
        "rewritten_query": "what is this book about?",
        "tool_required": True,
        "tool_categories": ["rag"],
        "allowed_tool_names": [
            "inspect_loaded_documents",
            "analyze_loaded_document",
            "rag_search",
        ],
        "primary_tool": "analyze_loaded_document",
        "planner_mode": "select_tools",
        "planner_tool_hints": ["analyze_loaded_document"],
        "document_query_intent": "summary",
        "document_summary_focus": "premise",
        "document_answer_mode": "synthesized",
    }
    llm_request = SimpleNamespace(
        tool_categories=None,
        force_tool=None,
        system_prompt=None,
        rag_files=["/tmp/doc.pdf"],
        planner_mode=None,
        final_system_prompt=None,
        attached_document_capabilities=capabilities,
        attached_document_total_tokens=42,
        attached_document_total_characters=128,
        rewritten_prompt=None,
        preprocessed_primary_tool=None,
    )
    data = {
        "request_data": {
            "prompt": "what is it about?",
            "action": LLMActionType.CHAT,
        }
    }

    result = mixin._prepare_request_tooling(data, llm_request)

    assert result[2] == "planner prompt"
    assert llm_request.force_tool is None
    assert llm_request.planner_mode == "select_tools"
    assert llm_request.final_system_prompt == "final chat prompt"
    assert llm_request.document_query_intent == "summary"
    assert llm_request.document_summary_focus == "premise"
    assert llm_request.request_plan.primary_tool == "analyze_loaded_document"
    assert llm_request.request_plan.planner_mode == "select_tools"
    mixin._apply_tool_filter.assert_called_once_with(
        ["rag"],
        action=LLMActionType.CHAT,
        force_tool=None,
        allowed_tool_names=[
            "inspect_loaded_documents",
            "analyze_loaded_document",
            "rag_search",
        ],
    )
    mixin.get_tool_planner_system_prompt.assert_called_once_with(
        LLMActionType.CHAT,
        tool_categories=["rag"],
        planner_tool_hints=["analyze_loaded_document"],
        attached_document_capabilities=capabilities,
        attached_document_total_tokens=42,
        attached_document_total_characters=128,
    )
    mixin.get_system_prompt_with_context.assert_called_once_with(
        LLMActionType.CHAT,
        None,
        None,
    )


def test_prepare_request_tooling_appends_rewritten_prompt_guidance():
    """Rewritten prompts should be injected into the system prompt only."""
    mixin = _DummyRequestHandlingMixin()
    mixin._preprocess_request.return_value = {
        "rewrite_needed": True,
        "rewritten_query": "Search the web for the latest Linux release notes.",
        "tool_required": True,
        "tool_categories": ["search"],
        "primary_tool": "search_web",
        "planner_tool_hints": ["search_web"],
        "document_query_intent": None,
        "document_summary_focus": None,
        "document_answer_mode": None,
    }
    llm_request = SimpleNamespace(
        tool_categories=None,
        force_tool=None,
        system_prompt=None,
        rewritten_prompt=None,
        preprocessed_primary_tool=None,
    )
    data = {
        "request_data": {
            "prompt": "latest linux release notes",
            "action": LLMActionType.CHAT,
        }
    }

    result = mixin._prepare_request_tooling(data, llm_request)

    assert "Internal request preprocess:" in result[2]
    assert "Canonical request:" in result[2]
    assert llm_request.rewritten_prompt == (
        "Search the web for the latest Linux release notes."
    )
    assert llm_request.force_tool == "search_web"


def test_prepare_request_tooling_skips_preprocess_for_explicit_force_tool():
    """Explicit tool forcing should bypass the LLM preprocessor."""
    mixin = _DummyRequestHandlingMixin()
    llm_request = SimpleNamespace(
        tool_categories=["search"],
        force_tool="search_web",
        system_prompt=None,
        rewritten_prompt=None,
        preprocessed_primary_tool=None,
    )
    data = {
        "request_data": {
            "prompt": "search for linux release notes",
            "action": LLMActionType.CHAT,
        }
    }

    mixin._prepare_request_tooling(data, llm_request)

    mixin._preprocess_request.assert_not_called()
    assert llm_request.preprocessed_primary_tool == "search_web"
    assert llm_request.request_plan.primary_tool == "search_web"
    assert llm_request.request_plan.allowed_tool_names == ["search_web"]