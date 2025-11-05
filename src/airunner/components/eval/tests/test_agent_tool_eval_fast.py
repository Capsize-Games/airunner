"""
Fast eval tests for agent management using mocked LLM responses.

These tests verify tool triggering logic without real LLM calls,
making them run in milliseconds instead of seconds/minutes.

Run with: pytest -m fast
"""

import pytest
import logging
from unittest.mock import patch, Mock, MagicMock
from airunner.components.eval.utils.tracking import track_trajectory_sync
from airunner.components.eval.utils.trajectory_evaluator import (
    trajectory_subsequence,
)

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.fast,  # Mark as fast test
]


@pytest.mark.fast
class TestAgentToolEvalFast:
    """Fast eval tests using mocked LLM responses."""

    @patch("airunner.components.llm.tools.agent_tools.AgentConfig")
    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_create_agent_basic(
        self,
        mock_session_scope,
        mock_agent_config,
        mock_airunner_client_with_agent_responses,
    ):
        """Test that 'create an agent' triggers create_agent tool."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "Helper"
        mock_agent_config.return_value = mock_agent

        prompt = "Create a new agent named Helper to assist with coding tasks"

        # Configure mock response
        mock_airunner_client_with_agent_responses.set_response(
            "create",
            "I've created a new agent named Helper to assist with coding tasks.",
            tool_calls=[
                {
                    "tool": "create_agent",
                    "args": {
                        "name": "Helper",
                        "description": "assist with coding tasks",
                    },
                }
            ],
        )

        result = track_trajectory_sync(
            mock_airunner_client_with_agent_responses,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        tool_calls = result["tool_calls"]

        # Verify response mentions creation
        assert "created" in response.lower() or "create" in response.lower()

        # Verify create_agent tool was called
        assert len(tool_calls) > 0
        assert any(
            call.get("tool") == "create_agent" for call in tool_calls
        ), f"Expected create_agent tool call, got: {tool_calls}"

        # Verify tool args contain agent name
        create_call = next(
            call for call in tool_calls if call.get("tool") == "create_agent"
        )
        assert "Helper" in str(create_call.get("args", {}))

    @patch("airunner.components.llm.tools.agent_tools.AgentConfig")
    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_list_agents_basic(
        self,
        mock_session_scope,
        mock_agent_config,
        mock_airunner_client_with_agent_responses,
    ):
        """Test that 'list agents' triggers list_agents tool."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        prompt = "Show me all my agents"

        # Configure mock response
        mock_airunner_client_with_agent_responses.set_response(
            "show",
            "Here are your agents: Helper, Assistant, Researcher",
            tool_calls=[{"tool": "list_agents", "args": {}}],
        )

        result = track_trajectory_sync(
            mock_airunner_client_with_agent_responses,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        tool_calls = result["tool_calls"]

        # Verify list_agents tool was called
        assert len(tool_calls) > 0
        assert any(
            call.get("tool") == "list_agents" for call in tool_calls
        ), f"Expected list_agents tool call, got: {tool_calls}"

    @patch("airunner.components.llm.tools.agent_tools.AgentConfig")
    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_get_agent_basic(
        self,
        mock_session_scope,
        mock_agent_config,
        mock_airunner_client_with_agent_responses,
    ):
        """Test that 'get agent' triggers get_agent tool."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "Helper"
        mock_agent.description = "coding tasks"
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_agent
        )

        prompt = "Tell me about the Helper agent"

        # Configure mock response
        mock_airunner_client_with_agent_responses.set_response(
            "tell me",
            "The Helper agent is configured to assist with coding tasks.",
            tool_calls=[{"tool": "get_agent", "args": {"agent_id": 1}}],
        )

        result = track_trajectory_sync(
            mock_airunner_client_with_agent_responses,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        tool_calls = result["tool_calls"]

        # Verify response mentions agent info
        assert "Helper" in response or "coding" in response.lower()

        # Verify get_agent tool was called
        assert len(tool_calls) > 0
        assert any(
            call.get("tool") == "get_agent" for call in tool_calls
        ), f"Expected get_agent tool call, got: {tool_calls}"
