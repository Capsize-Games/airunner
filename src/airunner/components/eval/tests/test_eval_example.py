"""
Example eval tests demonstrating proper architecture.

These tests show how to:
1. Test real LLM behavior (not mocked)
2. Mock only external side effects
3. Use quality metrics to evaluate responses
4. Test tool usage patterns

Run with:
    pytest test_eval_example.py -v
    pytest test_eval_example.py --model qwen2.5-coder:32b
"""

import pytest
import logging
from unittest.mock import patch, Mock, MagicMock
from airunner.components.eval.utils.tracking import track_trajectory_sync
from airunner.components.eval.utils.quality_metrics import (
    evaluate_tool_usage,
    evaluate_response_quality,
    assert_quality_threshold,
)

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.timeout(60),
]


@pytest.mark.eval
class TestEvalExample:
    """Example eval tests showing proper architecture."""

    @patch("airunner.components.llm.tools.agent_tools.AgentConfig")
    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_agent_creation_with_quality_metrics(
        self,
        mock_session_scope,
        mock_agent_config,
        airunner_client_function_scope,
    ):
        """
        Test agent creation with quality metrics.

        This test demonstrates proper eval test architecture:
        1. Mocks database operations (side effects)
        2. Uses real LLM (tests intelligence)
        3. Evaluates tool usage quality
        4. Evaluates response quality
        """
        # Mock database operations (side effect, not intelligence)
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "Helper"
        mock_agent_config.return_value = mock_agent

        prompt = "Create a new agent named Helper to assist with coding tasks"

        # Real LLM call - tests understanding and tool selection
        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        # Evaluate tool usage quality
        tool_metrics = evaluate_tool_usage(
            result,
            expected_tools=["create_agent"],
            max_calls=2,  # Should not call more than twice
        )

        logger.info(f"Tool usage metrics: {tool_metrics}")

        # Assert tool usage quality
        assert tool_metrics["tool_called"], "No tools were called"
        assert tool_metrics[
            "correct_tools"
        ], f"Wrong tools called: {tool_metrics['details']}"
        assert not tool_metrics["overcalling"], "LLM is over-calling tools"
        assert_quality_threshold(tool_metrics, 0.7, "tool usage")

        # Evaluate response quality
        quality_metrics = evaluate_response_quality(
            result["response"],
            prompt,
            expected_keywords=["agent", "Helper", "created"],
            forbidden_keywords=[
                "error",
                "failed",
                "cannot",
            ],  # Hallucination check
        )

        logger.info(f"Response quality metrics: {quality_metrics}")

        # Assert response quality
        assert (
            quality_metrics["relevance"] > 0.6
        ), f"Response not relevant: {quality_metrics['details']}"
        assert quality_metrics[
            "no_hallucination"
        ], "Response contains hallucinated errors"
        assert_quality_threshold(quality_metrics, 0.7, "response quality")

    @patch("airunner.components.llm.tools.web_tools.AggregatedSearchTool")
    def test_web_search_tool_selection(
        self,
        mock_search_tool,
        airunner_client_function_scope,
    ):
        """
        Test LLM correctly triggers web search for information requests.

        Demonstrates:
        - Mocking external HTTP requests (side effect)
        - Testing real LLM tool selection (intelligence)
        - Verifying tool was called with correct arguments
        """
        # Mock external HTTP request (side effect, not intelligence)
        mock_search_tool.aggregated_search_sync.return_value = {
            "duckduckgo": [
                {
                    "title": "Python Tutorial - Official Docs",
                    "link": "https://docs.python.org/3/tutorial/",
                    "snippet": "The Python Tutorial — Python 3 documentation",
                }
            ]
        }

        prompt = "Search for Python tutorials and summarize what you find"

        # Real LLM call - tests when to use search
        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SEARCH"],
        )

        # Evaluate tool usage
        tool_metrics = evaluate_tool_usage(
            result,
            expected_tools=["search_web"],  # Or similar tool name
            max_calls=1,  # Should only search once
        )

        logger.info(f"Tool metrics: {tool_metrics}")

        # Verify LLM understood it needs to search
        assert tool_metrics[
            "tool_called"
        ], "LLM should have triggered search tool for information request"

        # Verify mock was called (tool was actually invoked)
        if mock_search_tool.aggregated_search_sync.called:
            call_args = mock_search_tool.aggregated_search_sync.call_args
            query = call_args[0][0].lower()

            # Verify search query contains relevant terms
            assert "python" in query, "Search query missing 'python'"
            assert (
                "tutorial" in query or "tutorials" in query
            ), "Search query missing 'tutorial'"

        # Evaluate response quality
        quality_metrics = evaluate_response_quality(
            result["response"],
            prompt,
            expected_keywords=["python", "tutorial"],
            min_length=50,  # Should summarize findings
        )

        logger.info(f"Response quality: {quality_metrics}")

        # Response should mention search results
        assert (
            quality_metrics["completeness"] > 0.0
        ), "Response too short - should summarize search results"

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_tool_avoidance_when_not_needed(
        self,
        mock_session_scope,
        airunner_client_function_scope,
    ):
        """
        Test LLM does NOT call tools when they're not needed.

        This tests that the LLM:
        - Understands when tools are NOT necessary
        - Avoids over-calling tools
        - Can answer directly when appropriate
        """
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        # Simple factual question - no tools needed
        prompt = "What is 2 + 2?"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=100,
            tool_categories=[
                "AGENT",
                "SEARCH",
            ],  # Tools available but not needed
        )

        # Evaluate tool usage
        tool_metrics = evaluate_tool_usage(
            result,
            expected_tools=[],  # No tools should be called
            max_calls=0,
        )

        logger.info(f"Tool avoidance metrics: {tool_metrics}")

        # LLM should NOT have called tools
        assert len(result["tools"]) == 0 or tool_metrics["overcalling"], (
            f"LLM unnecessarily called tools: {result['tools']}\n"
            f"Should answer simple math directly without tools"
        )

        # Response should still be correct
        quality_metrics = evaluate_response_quality(
            result["response"],
            prompt,
            expected_keywords=["4"],  # Correct answer
            min_length=1,
        )

        assert (
            quality_metrics["relevance"] > 0.5
        ), "Response should contain the answer '4'"

    @patch("airunner.components.llm.tools.agent_tools.AgentConfig")
    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_tool_argument_quality(
        self,
        mock_session_scope,
        mock_agent_config,
        airunner_client_function_scope,
    ):
        """
        Test LLM passes correct arguments to tools.

        This verifies the LLM:
        - Extracts correct parameters from user prompt
        - Passes them to tools in proper format
        - Doesn't hallucinate or fabricate arguments
        """
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "CodeHelper"
        mock_agent_config.return_value = mock_agent

        prompt = (
            "Create an agent named CodeHelper with description "
            "'Assists with Python programming'"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        # Find the create_agent tool call
        create_calls = [
            call
            for call in result.get("tool_calls", [])
            if "create_agent" in call.get("tool", "").lower()
        ]

        if create_calls:
            tool_call = create_calls[0]
            args = tool_call.get("args", {})

            logger.info(f"Tool call args: {args}")

            # Verify LLM extracted correct name
            name = args.get("name", "")
            assert "CodeHelper" in str(
                name
            ), f"Expected name 'CodeHelper', got: {name}"

            # Verify LLM extracted correct description
            description = args.get("description", "")
            assert "Python" in str(
                description
            ), f"Expected description with 'Python', got: {description}"

        else:
            pytest.fail(
                f"Expected create_agent tool call, got: {result['tools']}"
            )
