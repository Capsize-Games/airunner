from types import SimpleNamespace
from unittest.mock import Mock

from airunner.components.llm.managers.llm_model_manager import LLMModelManager
from airunner.components.llm.managers.llm_request import LLMRequest
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
    def test_detects_simple_greeting_prompt(self):
        assert LLMModelManager._is_simple_greeting_prompt("hello") is True
        assert LLMModelManager._is_simple_greeting_prompt("good morning!") is True
        assert LLMModelManager._is_simple_greeting_prompt(
            "what is your name?"
        ) is False

    def test_detects_simple_no_tool_prompt(self):
        assert LLMModelManager._is_simple_no_tool_prompt(
            "tell me a joke"
        ) is True
        assert LLMModelManager._is_simple_no_tool_prompt(
            "what can you do?"
        ) is True
        assert LLMModelManager._is_simple_no_tool_prompt(
            "what is your name?"
        ) is True
        assert LLMModelManager._is_simple_no_tool_prompt(
            "tell me another"
        ) is True

    def test_chat_action_allows_auto_tool_selection(self):
        request = LLMRequest.for_action(LLMActionType.CHAT)

        assert request.tool_categories is None

    def test_detects_time_prompt_for_direct_tool_routing(self):
        categories, force_tool = LLMModelManager._detect_simple_tool_route(
            "what time is it?"
        )

        assert categories == ["system"]
        assert force_tool == "get_current_datetime"

    def test_detects_date_prompt_for_direct_tool_routing(self):
        categories, force_tool = LLMModelManager._detect_simple_tool_route(
            "what's today's date?"
        )

        assert categories == ["system"]
        assert force_tool == "get_current_datetime"

    def test_does_not_route_unrelated_prompt(self):
        categories, force_tool = LLMModelManager._detect_simple_tool_route(
            "what time does the meeting start tomorrow?"
        )

        assert categories is None
        assert force_tool is None

    def test_classifier_skips_tools_for_simple_no_tool_prompt(self):
        manager = MockToolClassifier()

        assert manager._classify_prompt_for_tools("tell me a joke") == []
        manager._workflow_manager._original_chat_model.invoke.assert_not_called()

    def test_empty_categories_disable_all_tools_for_simple_no_tool_prompt(
        self,
    ):
        manager = MockToolFilter("tell me a joke")

        manager._apply_tool_filter([])

        manager._workflow_manager.update_tools.assert_called_once_with([])
        manager._workflow_manager._build_and_compile_workflow.assert_called_once_with()
        manager._tool_manager.get_tools_by_categories.assert_not_called()