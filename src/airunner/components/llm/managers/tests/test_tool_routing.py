from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.components.llm.managers.llm_model_manager import LLMModelManager
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.components.llm.managers.request_plan import RequestPlan
from airunner.components.llm.managers.mixins.tool_classification_mixin import (
    ToolClassificationMixin,
)
from airunner.components.llm.managers.mixins.tool_filtering_mixin import (
    ToolFilteringMixin,
)
from airunner.enums import LLMActionType


class MockToolClassifier(ToolClassificationMixin):
    def __init__(self):
        self.logger = Mock()
        self._conversation_history_manager = Mock()
        self._tool_manager = SimpleNamespace(
            get_all_tools=lambda include_deferred=True: [
                SimpleNamespace(
                    name="get_current_datetime",
                    description="Get the current local date and time.",
                    category=ToolCategory.SYSTEM,
                ),
                SimpleNamespace(
                    name="search_web",
                    description="Search the web for current information.",
                    category=ToolCategory.SEARCH,
                ),
                SimpleNamespace(
                    name="analyze_loaded_document",
                    description="Prepare whole-document analysis context.",
                    category=ToolCategory.RAG,
                ),
            ]
        )
        self._workflow_manager = SimpleNamespace(
            _original_chat_model=Mock(),
        )


class MockToolFilter(ToolClassificationMixin, ToolFilteringMixin):
    def __init__(self, prompt: str):
        self.logger = Mock()
        self.llm_request = SimpleNamespace(prompt=prompt)
        self._workflow_manager = Mock()
        self._tool_manager = Mock()


class TestToolRouting:
    def test_chat_action_allows_auto_tool_selection(self):
        request = LLMRequest.for_action(LLMActionType.CHAT)

        assert request.tool_categories is None

    def test_preprocess_request_parses_primary_tool_and_categories(self):
        manager = MockToolClassifier()
        manager._workflow_manager._original_chat_model.invoke.return_value = (
            SimpleNamespace(
                content=(
                    '{"rewrite_needed": false, '
                    '"rewritten_query": "what time is it?", '
                    '"tool_required": true, '
                    '"tool_categories": ["system"], '
                    '"primary_tool": "get_current_datetime", '
                    '"planner_tool_hints": ["get_current_datetime"], '
                    '"document_query_intent": "none", '
                    '"document_summary_focus": "none", '
                    '"document_answer_mode": "none"}'
                )
            )
        )

        result = manager._preprocess_request(
            "what time is it?",
            action=LLMActionType.CHAT,
            llm_request=SimpleNamespace(rag_files=[]),
            conversation=None,
        )

        assert result["rewrite_needed"] is False
        assert result["rewritten_query"] == "what time is it?"
        assert result["tool_required"] is True
        assert result["tool_categories"] == ["system"]
        assert result["allowed_tool_names"] == ["get_current_datetime"]
        assert result["primary_tool"] == "get_current_datetime"
        assert result["planner_mode"] is None
        assert result["planner_tool_hints"] == ["get_current_datetime"]
        assert result["document_query_intent"] is None
        assert result["document_summary_focus"] is None
        assert result["document_answer_mode"] is None
        assert result["request_plan"] == RequestPlan(
            rewrite_needed=False,
            rewritten_query="what time is it?",
            tool_required=True,
            tool_categories=["system"],
            allowed_tool_names=["get_current_datetime"],
            primary_tool="get_current_datetime",
            planner_mode=None,
            planner_tool_hints=["get_current_datetime"],
            document_query_intent=None,
            document_summary_focus=None,
            document_answer_mode=None,
            answer_strategy="compose",
            finalization_mode=None,
        )

    def test_preprocess_request_strips_reasoning_markup(self):
        manager = MockToolClassifier()
        manager._workflow_manager._original_chat_model.invoke.return_value = (
            SimpleNamespace(
                content=(
                    "<think>internal reasoning</think>\n"
                    '{"rewrite_needed": true, '
                    '"rewritten_query": "Search the web for Linux release notes.", '
                    '"tool_required": true, '
                    '"tool_categories": ["search"], '
                    '"primary_tool": "search_web", '
                    '"planner_tool_hints": ["search_web"], '
                    '"document_query_intent": "none", '
                    '"document_summary_focus": "none", '
                    '"document_answer_mode": "none"}'
                )
            )
        )

        result = manager._preprocess_request(
            "latest linux release notes",
            action=LLMActionType.CHAT,
            llm_request=SimpleNamespace(rag_files=[]),
            conversation=None,
        )

        assert result["rewrite_needed"] is True
        assert result["rewritten_query"] == (
            "Search the web for Linux release notes."
        )
        assert result["primary_tool"] == "search_web"

    def test_preprocess_request_adds_primary_tool_category_when_missing(self):
        manager = MockToolClassifier()
        manager._workflow_manager._original_chat_model.invoke.return_value = (
            SimpleNamespace(
                content=(
                    '{"rewrite_needed": false, '
                    '"rewritten_query": "explain this book to me", '
                    '"tool_required": true, '
                    '"tool_categories": ["analysis"], '
                    '"primary_tool": "analyze_loaded_document", '
                    '"planner_tool_hints": ["analyze_loaded_document"], '
                    '"document_query_intent": "summary", '
                    '"document_summary_focus": "premise", '
                    '"document_answer_mode": "synthesized"}'
                )
            )
        )

        result = manager._preprocess_request(
            "explain this book to me",
            action=LLMActionType.CHAT,
            llm_request=SimpleNamespace(rag_files=["/tmp/book.epub"]),
            conversation=None,
        )

        assert result["primary_tool"] == "analyze_loaded_document"
        assert "rag" in result["tool_categories"]
        assert result["allowed_tool_names"] == ["analyze_loaded_document"]
        assert result["document_query_intent"] == "summary"
        assert result["document_summary_focus"] == "premise"
        assert result["request_plan"].document_answer_mode == "synthesized"

    def test_empty_categories_disable_all_tools_for_simple_no_tool_prompt(
        self,
    ):
        manager = MockToolFilter("anything")

        manager._apply_tool_filter([])

        manager._workflow_manager.update_tools.assert_called_once_with([])
        manager._workflow_manager._build_and_compile_workflow.assert_called_once_with()
        manager._tool_manager.get_tools_by_categories.assert_not_called()