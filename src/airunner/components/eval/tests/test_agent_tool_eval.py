"""
Eval tests for agent management tool triggering with natural language.

Tests that the LLM agent can correctly trigger agent creation and management
tools when given natural language prompts like:
- "create a new agent named Helper"
- "list all my agents"
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
    pytest.mark.timeout(60),
]


@pytest.mark.eval
class TestAgentToolEval:
    """Eval tests for natural language agent tool triggering."""

    @patch("airunner.components.llm.tools.agent_tools.AgentConfig")
    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_create_agent_basic(
        self,
        mock_session_scope,
        mock_agent_config,
        airunner_client_function_scope,
    ):
        """Test that 'create an agent' triggers create_agent tool."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "Helper"
        mock_agent_config.return_value = mock_agent

        prompt = "Create a new agent named Helper to assist with coding tasks"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        trajectory = result["trajectory"]
        tools = result["tools"]

        # Verify create tool was called or response acknowledges creation
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert (
            mock_agent_config.called
            or "created" in response_text
            or "agent" in response_text
            or "helper" in response_text
        )

        # Verify trajectory includes agent creation tool
        expected_trajectory = ["model", "create_agent", "model"]
        score = trajectory_subsequence(
            result, {"trajectory": expected_trajectory}
        )
        assert (
            score >= 0.66
        ), f"Expected create_agent in trajectory, got: {trajectory}"

        # Verify create_agent tool was used
        assert (
            "create_agent" in tools
        ), f"Expected create_agent in tools, got: {tools}"

    @patch("airunner.components.llm.tools.agent_tools.AgentConfig")
    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_create_agent_variations(
        self,
        mock_session_scope,
        mock_agent_config,
        airunner_client_function_scope,
    ):
        """Test various phrasings that should trigger agent creation."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent_config.return_value = mock_agent

        test_prompts = [
            "make a new agent called Assistant",
            "I need you to create an agent for research",
            "set up a new AI agent named Researcher",
            "can you create an agent to help me write?",
        ]

        for prompt in test_prompts:
            mock_agent_config.reset_mock()

            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=400,
                tool_categories=["AGENT"],
            )

            response = result["response"]
            tools = result["tools"]

            # Should attempt to create agent
            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )
            assert (
                mock_agent_config.called
                or "created" in response_text
                or "agent" in response_text
            ), f"Failed to trigger create for: {prompt}"

            # Verify create_agent tool was used
            assert (
                "create_agent" in tools
            ), f"Expected create_agent for prompt: {prompt}, got tools: {tools}"

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_list_agents_basic(
        self, mock_session_scope, airunner_client_function_scope
    ):
        """Test that 'list agents' triggers list_agents tool."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.all.return_value = [
            Mock(id=1, name="Helper", system_message="Helps with tasks"),
            Mock(id=2, name="Coder", system_message="Writes code"),
        ]
        mock_session_scope.return_value.__enter__.return_value = mock_session

        prompt = "List all my agents"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        trajectory = result["trajectory"]
        tools = result["tools"]

        # Verify list tool was called
        assert mock_session.query.called

        # Verify trajectory includes list_agents tool
        expected_trajectory = ["model", "list_agents", "model"]
        score = trajectory_subsequence(
            result, {"trajectory": expected_trajectory}
        )
        assert (
            score >= 0.66
        ), f"Expected list_agents in trajectory, got: {trajectory}"

        # Verify list_agents tool was used
        assert (
            "list_agents" in tools
        ), f"Expected list_agents in tools, got: {tools}"

        # Response should mention agents
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert (
            "helper" in response_text
            or "coder" in response_text
            or "agent" in response_text
        )

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_get_agent_basic(
        self, mock_session_scope, airunner_client_function_scope
    ):
        """Test that 'get agent X' triggers get_agent tool."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "Helper"
        mock_agent.system_message = "I help with tasks"
        mock_agent.model = "llama3"
        mock_query.filter_by.return_value.first.return_value = mock_agent

        mock_session_scope.return_value.__enter__.return_value = mock_session

        prompt = "Show me details about the Helper agent"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        trajectory = result["trajectory"]
        tools = result["tools"]

        # Verify get tool was called
        assert mock_session.query.called

        # Verify trajectory includes get_agent tool
        expected_trajectory = ["model", "get_agent", "model"]
        score = trajectory_subsequence(
            result, {"trajectory": expected_trajectory}
        )
        assert (
            score >= 0.66
        ), f"Expected get_agent in trajectory, got: {trajectory}"

        # Verify get_agent tool was used
        assert (
            "get_agent" in tools
        ), f"Expected get_agent in tools, got: {tools}"

        # Response should contain agent details
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert (
            "helper" in response_text
            or "tasks" in response_text
            or "agent" in response_text
        )

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_configure_agent_basic(
        self, mock_session_scope, airunner_client_function_scope
    ):
        """Test that 'configure agent X' triggers configure_agent tool."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "Helper"
        mock_agent.system_message = "Old message"
        mock_query.filter_by.return_value.first.return_value = mock_agent

        mock_session_scope.return_value.__enter__.return_value = mock_session

        prompt = "Configure the Helper agent to be more friendly"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        trajectory = result["trajectory"]
        tools = result["tools"]

        # Verify configure was attempted
        assert mock_session.query.called or mock_session.commit.called

        # Verify trajectory includes configure_agent tool
        expected_trajectory = ["model", "configure_agent", "model"]
        score = trajectory_subsequence(
            result, {"trajectory": expected_trajectory}
        )
        assert (
            score >= 0.66
        ), f"Expected configure_agent in trajectory, got: {trajectory}"

        # Verify configure_agent tool was used
        assert (
            "configure_agent" in tools
        ), f"Expected configure_agent in tools, got: {tools}"

        # Response should acknowledge configuration
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert (
            "configured" in response_text
            or "updated" in response_text
            or "helper" in response_text
        )

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_delete_agent_basic(
        self, mock_session_scope, airunner_client_function_scope
    ):
        """Test that 'delete agent X' triggers delete_agent tool."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query

        mock_agent = Mock()
        mock_agent.id = 1
        mock_agent.name = "OldAgent"
        mock_query.filter_by.return_value.first.return_value = mock_agent

        mock_session_scope.return_value.__enter__.return_value = mock_session

        prompt = "Delete the OldAgent agent, I don't need it anymore"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=400,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        trajectory = result["trajectory"]
        tools = result["tools"]

        # Verify delete was attempted
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert (
            mock_session.delete.called
            or "deleted" in response_text
            or "removed" in response_text
            or "oldagent" in response_text
        )

        # Verify trajectory includes delete_agent tool
        expected_trajectory = ["model", "delete_agent", "model"]
        score = trajectory_subsequence(
            result, {"trajectory": expected_trajectory}
        )
        assert (
            score >= 0.66
        ), f"Expected delete_agent in trajectory, got: {trajectory}"

        # Verify delete_agent tool was used
        assert (
            "delete_agent" in tools
        ), f"Expected delete_agent in tools, got: {tools}"

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    @patch("airunner.components.llm.tools.agent_tools.list_agent_templates")
    def test_list_templates_basic(
        self,
        mock_list_templates,
        mock_session_scope,
        airunner_client_function_scope,
    ):
        """Test that 'list agent templates' triggers list_agent_templates."""
        mock_list_templates.return_value = [
            {"name": "assistant", "description": "General assistant"},
            {"name": "coder", "description": "Coding specialist"},
        ]

        prompt = "What agent templates are available?"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        trajectory = result["trajectory"]
        tools = result["tools"]

        # Verify templates were listed
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert (
            mock_list_templates.called
            or "template" in response_text
            or "assistant" in response_text
            or "coder" in response_text
        )

        # Verify trajectory includes list_agent_templates tool
        expected_trajectory = ["model", "list_agent_templates", "model"]
        score = trajectory_subsequence(
            result, {"trajectory": expected_trajectory}
        )
        assert (
            score >= 0.66
        ), f"Expected list_agent_templates in trajectory, got: {trajectory}"

        # Verify list_agent_templates tool was used
        assert (
            "list_agent_templates" in tools
        ), f"Expected list_agent_templates in tools, got: {tools}"


@pytest.mark.eval
class TestAgentToolErrorHandling:
    """Test that agent handles agent tool errors gracefully."""

    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_get_nonexistent_agent(
        self, mock_session_scope, airunner_client_function_scope
    ):
        """Test handling when requested agent doesn't exist."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value.first.return_value = None
        mock_session_scope.return_value.__enter__.return_value = mock_session

        prompt = "Show me the NonexistentAgent agent"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        tools = result["tools"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        # Should acknowledge missing agent
        assert (
            "not found" in response_text
            or "doesn't exist" in response_text
            or "couldn't find" in response_text
            or "no agent" in response_text
        )

        # Should still attempt to get agent
        assert "get_agent" in tools

    @patch("airunner.components.llm.tools.agent_tools.AgentConfig")
    @patch("airunner.components.llm.tools.agent_tools.session_scope")
    def test_create_duplicate_agent(
        self,
        mock_session_scope,
        mock_agent_config,
        airunner_client_function_scope,
    ):
        """Test handling when trying to create agent with existing name."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        # Simulate integrity error (generic exception to avoid import issues)
        mock_session.add.side_effect = Exception("UNIQUE constraint failed")

        prompt = "Create an agent named Helper"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=400,
            tool_categories=["AGENT"],
        )

        response = result["response"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        # Should handle error gracefully
        assert (
            "error" in response_text
            or "already exists" in response_text
            or "couldn't create" in response_text
        )
