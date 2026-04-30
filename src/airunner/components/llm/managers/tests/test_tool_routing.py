from airunner.components.llm.managers.llm_model_manager import LLMModelManager


class TestToolRouting:
    def test_detects_simple_greeting_prompt(self):
        assert LLMModelManager._is_simple_greeting_prompt("hello") is True
        assert LLMModelManager._is_simple_greeting_prompt("good morning!") is True

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