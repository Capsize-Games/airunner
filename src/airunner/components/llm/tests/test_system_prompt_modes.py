"""
Unit tests for automatic system prompt mode switching.

Tests that the LLM manager correctly switches between math, precision,
and conversational modes based on tool categories.
"""

from typing import Optional

import pytest

from airunner.components.llm.core.tool_registry import ToolCategory
from airunner.components.llm.managers.mixins.system_prompt_mixin import (
    SystemPromptMixin,
    MATH_SYSTEM_PROMPT,
    PRECISION_SYSTEM_PROMPT,
)
from airunner.enums import LLMActionType


class MockSystemPromptClass(SystemPromptMixin):
    """Mock class to test SystemPromptMixin."""

    def get_system_prompt_for_action(
        self, action: LLMActionType, force_tool: Optional[str] = None
    ) -> str:
        """Mock implementation that returns a conversational prompt."""
        base = f"Conversational prompt for {action.name}"
        if force_tool:
            base += f" [forced: {force_tool}]"
        return base


class TestSystemPromptModes:
    """Test automatic system prompt mode switching."""

    @pytest.fixture
    def prompt_manager(self):
        """Create a mock prompt manager instance."""
        return MockSystemPromptClass()

    def test_math_mode_with_math_category(self, prompt_manager):
        """Test that MATH tools trigger math mode."""
        result = prompt_manager.get_system_prompt_with_context(
            action=LLMActionType.CHAT,
            tool_categories=[ToolCategory.MATH.value],
        )

        assert result == MATH_SYSTEM_PROMPT
        assert "mathematics expert" in result
        assert "sympy_compute" in result
        assert "date" not in result.lower()  # No date/time context

    def test_math_mode_with_math_and_analysis(self, prompt_manager):
        """Test that MATH + ANALYSIS still uses math mode (math takes priority)."""
        result = prompt_manager.get_system_prompt_with_context(
            action=LLMActionType.CHAT,
            tool_categories=[
                ToolCategory.MATH.value,
                ToolCategory.ANALYSIS.value,
            ],
        )

        assert result == MATH_SYSTEM_PROMPT

    def test_precision_mode_with_analysis_only(self, prompt_manager):
        """Test that ANALYSIS tools trigger precision mode."""
        result = prompt_manager.get_system_prompt_with_context(
            action=LLMActionType.CHAT,
            tool_categories=[ToolCategory.ANALYSIS.value],
        )

        assert result == PRECISION_SYSTEM_PROMPT
        assert "precise technical assistant" in result

    def test_conversational_mode_with_no_categories(self, prompt_manager):
        """Test that no tool categories triggers conversational mode."""
        result = prompt_manager.get_system_prompt_with_context(
            action=LLMActionType.CHAT,
            tool_categories=None,
        )

        assert "Conversational" in result
        assert result == "Conversational prompt for CHAT"

    def test_conversational_mode_with_empty_list(self, prompt_manager):
        """Test that empty tool categories list triggers conversational mode."""
        result = prompt_manager.get_system_prompt_with_context(
            action=LLMActionType.CHAT,
            tool_categories=[],
        )

        assert "Conversational" in result

    def test_conversational_mode_with_other_categories(self, prompt_manager):
        """Test that non-math/analysis categories use conversational mode."""
        # Using a category that's not MATH or ANALYSIS
        result = prompt_manager.get_system_prompt_with_context(
            action=LLMActionType.CHAT,
            tool_categories=[ToolCategory.CHAT.value],
        )

        assert "Conversational" in result

    def test_get_prompt_mode_detection(self, prompt_manager):
        """Test the _get_prompt_mode method directly."""
        # Math mode
        mode = prompt_manager._get_prompt_mode([ToolCategory.MATH.value])
        assert mode == "math"

        # Precision mode
        mode = prompt_manager._get_prompt_mode([ToolCategory.ANALYSIS.value])
        assert mode == "precision"

        # Conversational mode
        mode = prompt_manager._get_prompt_mode(None)
        assert mode == "conversational"

        mode = prompt_manager._get_prompt_mode([])
        assert mode == "conversational"

    def test_mode_switching_with_tool_category_objects(self, prompt_manager):
        """Test that ToolCategory objects (not strings) work correctly."""
        result = prompt_manager.get_system_prompt_with_context(
            action=LLMActionType.CHAT,
            tool_categories=[ToolCategory.MATH],  # Object, not string
        )

        assert result == MATH_SYSTEM_PROMPT

    def test_math_prompt_content(self):
        """Test that math prompt has expected content."""
        assert "sympy_compute" in MATH_SYSTEM_PROMPT
        assert "numpy_compute" in MATH_SYSTEM_PROMPT
        assert "python_compute" in MATH_SYSTEM_PROMPT
        assert "polya_reasoning" in MATH_SYSTEM_PROMPT
        assert "result" in MATH_SYSTEM_PROMPT  # Mentions result variable
        assert "date" not in MATH_SYSTEM_PROMPT.lower()

    def test_precision_prompt_content(self):
        """Test that precision prompt has expected content."""
        assert "precise" in PRECISION_SYSTEM_PROMPT.lower()
        assert "technical" in PRECISION_SYSTEM_PROMPT.lower()
        assert "date" not in PRECISION_SYSTEM_PROMPT.lower()

    def test_mode_priority_math_over_precision(self, prompt_manager):
        """Test that MATH category takes priority over ANALYSIS."""
        result = prompt_manager.get_system_prompt_with_context(
            action=LLMActionType.CHAT,
            tool_categories=[
                ToolCategory.ANALYSIS.value,
                ToolCategory.MATH.value,  # Math should win
            ],
        )

        assert result == MATH_SYSTEM_PROMPT


class TestSystemPromptIntegration:
    """Integration tests for system prompt mode switching in real scenarios."""

    def test_math_problem_scenario(self):
        """Test expected behavior for a math problem scenario."""
        manager = MockSystemPromptClass()

        # When solving math with tools
        prompt = manager.get_system_prompt_with_context(
            action=LLMActionType.DECISION,
            tool_categories=[ToolCategory.MATH.value],
        )

        assert "mathematics" in prompt.lower()
        assert "sympy" in prompt
        # Should NOT have conversational elements
        assert "friendly" not in prompt.lower()
        assert "hello" not in prompt.lower()

    def test_conversational_chat_scenario(self):
        """Test expected behavior for normal chat scenario."""
        manager = MockSystemPromptClass()

        # When chatting normally (no special tools)
        prompt = manager.get_system_prompt_with_context(
            action=LLMActionType.CHAT,
            tool_categories=None,
        )

        assert "Conversational" in prompt
        # Should have action-specific prompt
        assert "CHAT" in prompt

    def test_technical_analysis_scenario(self):
        """Test expected behavior for technical analysis scenario."""
        manager = MockSystemPromptClass()

        # When doing analysis with reasoning tools
        prompt = manager.get_system_prompt_with_context(
            action=LLMActionType.DECISION,
            tool_categories=[ToolCategory.ANALYSIS.value],
        )


class TestForceToolInstruction:
    """Test force_tool parameter for slash commands."""

    def test_force_tool_adds_instruction_in_conversational_mode(self):
        """Test that force_tool adds instruction when in conversational mode."""
        manager = MockSystemPromptClass()

        # Force search_web tool
        prompt = manager.get_system_prompt_with_context(
            action=LLMActionType.CHAT,
            tool_categories=None,
            force_tool="search_web",
        )

        assert "forced: search_web" in prompt

    def test_force_tool_adds_instruction_in_math_mode(self):
        """Test that force_tool adds instruction even in math mode."""
        manager = MockSystemPromptClass()

        # Force a tool while in math mode
        prompt = manager.get_system_prompt_with_context(
            action=LLMActionType.CHAT,
            tool_categories=[ToolCategory.MATH.value],
            force_tool="search_web",
        )

        # Should still be math prompt but with force_tool instruction appended
        assert "mathematics" in prompt.lower()
        # search_web uses "RESEARCH MODE ACTIVATED" instead of "FORCED TOOL MODE"
        assert "RESEARCH MODE ACTIVATED" in prompt
        assert "search_web" in prompt

    def test_force_tool_with_precision_mode(self):
        """Test that force_tool adds instruction in precision mode."""
        manager = MockSystemPromptClass()

        prompt = manager.get_system_prompt_with_context(
            action=LLMActionType.CHAT,
            tool_categories=[ToolCategory.ANALYSIS.value],
            force_tool="generate_image",
        )

        # Should be precision prompt with force_tool instruction
        assert "precise technical assistant" in prompt
        assert "FORCED TOOL MODE" in prompt
        assert "generate_image" in prompt

    def test_no_force_tool_no_instruction(self):
        """Test that no force_tool means no forced tool instruction."""
        manager = MockSystemPromptClass()

        prompt = manager.get_system_prompt_with_context(
            action=LLMActionType.CHAT,
            tool_categories=None,
            force_tool=None,
        )

        assert "FORCED TOOL MODE" not in prompt
        assert "MUST use" not in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
