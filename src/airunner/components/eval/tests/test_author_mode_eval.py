"""
Eval tests for Author Mode with natural language prompts.

Tests that the mode-based routing correctly identifies author intent
and routes to the AuthorAgent which uses author-specific tools like:
- improve_writing()
- check_grammar()
- find_synonyms()
- analyze_writing_style()
"""

import pytest
import logging
from airunner.components.eval.utils.tracking import track_trajectory_sync
from airunner.components.eval.utils.trajectory_evaluator import (
    trajectory_contains,
    trajectory_tool_usage,
)

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.timeout(60),
]


@pytest.mark.eval
class TestAuthorModeEval:
    """Eval tests for Author Mode natural language triggering."""

    def test_improve_writing_basic(
        self,
        airunner_client_function_scope,
    ):
        """Test that writing improvement request routes to author mode."""
        prompt = (
            "Please improve this sentence: "
            "'The dog runned quickly to the park.'"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        result["trajectory"]
        tools = result["tools"]

        # Verify response addresses the writing improvement
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in ["ran", "improve", "corrected", "better"]
        ), f"Response doesn't address writing improvement: {response_text}"

        # Verify trajectory includes author tools
        author_tools = ["improve_writing", "check_grammar"]
        tool_usage_score = trajectory_tool_usage(result, author_tools)
        assert (
            tool_usage_score > 0.0
        ), f"Expected author tools usage, got tools: {tools}"

    def test_grammar_checking(
        self,
        airunner_client_function_scope,
    ):
        """Test that grammar checking request routes to author mode."""
        prompt = (
            "Check the grammar in this text: "
            "'Me and him went to the store yesterday.'"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response addresses grammar
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in ["grammar", "he and i", "correct", "should"]
        ), f"Response doesn't address grammar: {response_text}"

        # Verify check_grammar tool was used
        assert trajectory_contains(
            result, "check_grammar"
        ), f"Expected check_grammar tool, got: {tools}"

    def test_synonym_lookup(
        self,
        airunner_client_function_scope,
    ):
        """Test that synonym requests route to author mode."""
        prompt = "Find synonyms for the word 'happy'"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response provides synonyms
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in [
                "joyful",
                "cheerful",
                "glad",
                "pleased",
                "synonym",
            ]
        ), f"Response doesn't provide synonyms: {response_text}"

        # Verify find_synonyms tool was used
        assert trajectory_contains(
            result, "find_synonyms"
        ), f"Expected find_synonyms tool, got: {tools}"

    def test_writing_style_analysis(
        self,
        airunner_client_function_scope,
    ):
        """Test that style analysis requests route to author mode."""
        prompt = (
            "Analyze the writing style of this passage: "
            "'It was a dark and stormy night. The wind howled. "
            "Lightning flashed across the sky.'"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response analyzes style
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in [
                "style",
                "tone",
                "dramatic",
                "descriptive",
                "short sentences",
            ]
        ), f"Response doesn't analyze style: {response_text}"

        # Verify analyze_writing_style tool was used
        assert trajectory_contains(
            result, "analyze_writing_style"
        ), f"Expected analyze_writing_style tool, got: {tools}"

    def test_author_mode_trajectory_efficiency(
        self,
        airunner_client_function_scope,
    ):
        """Test that author mode uses efficient tool paths."""
        prompt = (
            "Improve this text and check grammar: "
            "'The quick brown fox jump over the lazy dog.'"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        trajectory = result["trajectory"]
        tools = result["tools"]

        # Verify trajectory is efficient (not too many redundant steps)
        # Should be: classify_intent -> author_agent -> tools -> response
        assert (
            len(trajectory) < 10
        ), f"Trajectory too long (inefficient): {trajectory}"

        # Verify appropriate author tools used
        author_tools_used = [
            t
            for t in tools
            if t
            in [
                "improve_writing",
                "check_grammar",
                "find_synonyms",
                "analyze_writing_style",
            ]
        ]
        assert len(author_tools_used) > 0, f"No author tools used: {tools}"
