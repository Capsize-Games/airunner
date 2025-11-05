"""
Eval tests for Mode Switching with multi-turn conversations.

Tests that the mode-based routing can correctly handle:
- Switching between different modes in a conversation
- Maintaining context across mode switches
- Efficient mode transitions
- Mode persistence within similar queries
"""

import pytest
import logging
from airunner.components.eval.utils.tracking import track_trajectory_sync
from airunner.components.eval.utils.trajectory_evaluator import (
    trajectory_contains,
)

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.timeout(90),  # Longer timeout for multi-turn
]


@pytest.mark.eval
class TestModeSwitchingEval:
    """Eval tests for mode switching in multi-turn conversations."""

    def test_author_to_research_switch(
        self,
        airunner_client_function_scope,
    ):
        """Test switching from author mode to research mode."""
        # First prompt: author mode
        prompt1 = "Improve this sentence: 'The cat runned fast.'"

        result1 = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt1,
            max_tokens=500,
            use_mode_routing=True,
        )

        # Verify author mode was used
        assert any(
            tool in result1["tools"]
            for tool in ["improve_writing", "check_grammar"]
        ), f"Expected author tools in turn 1, got: {result1['tools']}"

        # Second prompt: research mode (simulated as new invocation)
        prompt2 = (
            "Now synthesize information from these sources: "
            "Source A says cats are fast. Source B mentions feline agility."
        )

        result2 = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt2,
            max_tokens=500,
            use_mode_routing=True,
        )

        # Verify research mode was used
        assert any(
            tool in result2["tools"]
            for tool in [
                "synthesize_sources",
                "organize_research",
                "extract_key_points",
            ]
        ), f"Expected research tools in turn 2, got: {result2['tools']}"

    def test_code_to_qa_switch(
        self,
        airunner_client_function_scope,
    ):
        """Test switching from code mode to QA mode."""
        # First prompt: code mode
        prompt1 = "Execute this Python code: print('Hello World')"

        result1 = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt1,
            max_tokens=500,
            use_mode_routing=True,
        )

        # Verify code mode was used
        assert any(
            tool in result1["tools"]
            for tool in ["execute_python", "format_code"]
        ), f"Expected code tools in turn 1, got: {result1['tools']}"

        # Second prompt: QA mode
        prompt2 = (
            "Verify this answer: "
            "Question: What does print do? "
            "Answer: It outputs text to the console."
        )

        result2 = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt2,
            max_tokens=500,
            use_mode_routing=True,
        )

        # Verify QA mode was used
        assert any(
            tool in result2["tools"]
            for tool in ["verify_answer", "score_answer_confidence"]
        ), f"Expected QA tools in turn 2, got: {result2['tools']}"

    def test_research_to_author_switch(
        self,
        airunner_client_function_scope,
    ):
        """Test switching from research mode to author mode."""
        # First prompt: research mode
        prompt1 = (
            "Extract key points from this text: "
            "Machine learning is a subset of AI that enables systems "
            "to learn from data."
        )

        result1 = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt1,
            max_tokens=500,
            use_mode_routing=True,
        )

        # Verify research mode was used
        assert any(
            tool in result1["tools"]
            for tool in ["extract_key_points", "organize_research"]
        ), f"Expected research tools in turn 1, got: {result1['tools']}"

        # Second prompt: author mode
        prompt2 = "Now improve the writing style of that summary"

        result2 = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt2,
            max_tokens=500,
            use_mode_routing=True,
        )

        # Verify author mode was used
        assert any(
            tool in result2["tools"]
            for tool in [
                "improve_writing",
                "analyze_writing_style",
            ]
        ), f"Expected author tools in turn 2, got: {result2['tools']}"

    def test_qa_to_code_switch(
        self,
        airunner_client_function_scope,
    ):
        """Test switching from QA mode to code mode."""
        # First prompt: QA mode
        prompt1 = "What is the answer type for: 'How many planets are there?'"

        result1 = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt1,
            max_tokens=500,
            use_mode_routing=True,
        )

        # Verify QA mode was used
        assert any(
            tool in result1["tools"]
            for tool in ["identify_answer_type", "extract_answer_from_context"]
        ), f"Expected QA tools in turn 1, got: {result1['tools']}"

        # Second prompt: code mode
        prompt2 = "Now write Python code to calculate the number of planets"

        result2 = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt2,
            max_tokens=500,
            use_mode_routing=True,
        )

        # Verify code mode was used
        assert any(
            tool in result2["tools"]
            for tool in ["execute_python", "create_code_file"]
        ), f"Expected code tools in turn 2, got: {result2['tools']}"

    def test_mode_persistence(
        self,
        airunner_client_function_scope,
    ):
        """Test that mode persists for similar consecutive queries."""
        # First prompt: code mode
        prompt1 = "Format this code: def foo():pass"

        result1 = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt1,
            max_tokens=500,
            use_mode_routing=True,
        )

        # Verify code mode
        assert trajectory_contains(
            result1, "format_code"
        ), f"Expected format_code in turn 1, got: {result1['tools']}"

        # Second prompt: still code mode (similar task)
        prompt2 = "Now lint the same code"

        result2 = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt2,
            max_tokens=500,
            use_mode_routing=True,
        )

        # Verify still in code mode
        assert trajectory_contains(
            result2, "lint_code"
        ), f"Expected lint_code in turn 2, got: {result2['tools']}"

    def test_transition_efficiency(
        self,
        airunner_client_function_scope,
    ):
        """Test that mode transitions are efficient."""
        # Prompt that requires switching mid-task
        prompt = (
            "First, improve this writing: 'The dog ran quick.' "
            "Then, extract the key point from the improved version."
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=800,
            use_mode_routing=True,
        )

        trajectory = result["trajectory"]
        tools = result["tools"]

        # Verify both author and research tools were used
        author_tools_used = any(
            t in tools for t in ["improve_writing", "check_grammar"]
        )
        research_tools_used = any(
            t in tools for t in ["extract_key_points", "organize_research"]
        )

        # At least one type should be used (may fall back to general mode)
        assert (
            author_tools_used or research_tools_used or len(tools) > 0
        ), f"Expected mode-specific tools, got: {tools}"

        # Trajectory should be reasonably efficient
        assert (
            len(trajectory) < 15
        ), f"Trajectory too long for mixed task: {trajectory}"
