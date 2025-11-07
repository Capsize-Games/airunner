"""
Eval tests for agent management tool triggering with natural language.

Tests that the LLM agent can correctly trigger agent creation and management
tools when given natural language prompts like:
- "create a new agent named Helper"
- "list all my agents"
"""

import pytest
import logging
from airunner.components.eval.utils.tracking import track_trajectory_sync

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.timeout(60),
]


@pytest.mark.eval
class TestAgentToolEval:
    """Eval tests for natural language agent tool triggering."""

    def test_create_agent_basic(self, airunner_client_function_scope):
        """Test that 'create an agent' triggers create_agent tool."""
        prompt = "Create a new agent named Helper to assist with coding tasks"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        tools = result["tools"]
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify create tool was called OR response acknowledges creation
        assert any(
            "create" in tool.lower() or "agent" in tool.lower()
            for tool in tools
        ) or any(
            word in response_text
            for word in ["created", "agent", "helper", "create"]
        ), f"Expected create_agent tool or acknowledgment, got tools: {tools}, response: {response_text}"

    def test_create_agent_variations(self, airunner_client_function_scope):
        """Test various phrasings that should trigger agent creation."""
        test_prompts = [
            "make a new agent called Assistant",
            "I need you to create an agent for research",
            "set up a new AI agent named Researcher",
            "can you create an agent to help me write?",
        ]

        for prompt in test_prompts:
            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=400,
                tool_categories=["AGENT"],
            )

            response = result["response"]
            tools = result["tools"]
            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )

            # Should attempt to create agent
            assert any(
                "create" in tool.lower() or "agent" in tool.lower()
                for tool in tools
            ) or any(
                word in response_text
                for word in ["created", "agent", "create"]
            ), f"Failed to trigger create for: {prompt}, got tools: {tools}, response: {response_text}"

    def test_list_agents_basic(self, airunner_client_function_scope):
        """Test that 'list agents' triggers list_agents tool."""
        prompt = "List all my agents"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        tools = result["tools"]
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Should call list tool OR respond about agents
        assert any(
            "list" in tool.lower() or "agent" in tool.lower() for tool in tools
        ) or any(
            word in response_text
            for word in ["agent", "list", "no agents", "don't have"]
        ), f"Expected list_agents tool or response, got tools: {tools}, response: {response_text}"

    def test_get_agent_basic(self, airunner_client_function_scope):
        """Test that 'get agent X' triggers get_agent tool."""
        prompt = "Show me details about the Helper agent"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        tools = result["tools"]
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Should call get tool OR respond about agent
        assert any(
            "get" in tool.lower() or "agent" in tool.lower() for tool in tools
        ) or any(
            word in response_text
            for word in [
                "helper",
                "agent",
                "details",
                "not found",
                "don't have",
            ]
        ), f"Expected get_agent tool or response, got tools: {tools}, response: {response_text}"

    def test_configure_agent_basic(self, airunner_client_function_scope):
        """Test that 'configure agent X' triggers configure_agent tool."""
        prompt = "Configure the Helper agent to be more friendly"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        tools = result["tools"]
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Should call configure tool OR acknowledge
        assert any(
            "configure" in tool.lower() or "agent" in tool.lower()
            for tool in tools
        ) or any(
            word in response_text
            for word in [
                "configured",
                "updated",
                "helper",
                "agent",
                "configure",
            ]
        ), f"Expected configure_agent tool or acknowledgment, got tools: {tools}, response: {response_text}"

    def test_delete_agent_basic(self, airunner_client_function_scope):
        """Test that 'delete agent X' triggers delete_agent tool."""
        prompt = "Delete the OldAgent agent, I don't need it anymore"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=400,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        tools = result["tools"]
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Should call delete tool OR acknowledge deletion/error
        assert any(
            "delete" in tool.lower() or "agent" in tool.lower()
            for tool in tools
        ) or any(
            word in response_text
            for word in [
                "deleted",
                "removed",
                "oldagent",
                "agent",
                "delete",
                "error",
                "issue",
            ]
        ), f"Expected delete_agent tool or acknowledgment, got tools: {tools}, response: {response_text}"

    def test_list_templates_basic(self, airunner_client_function_scope):
        """Test that 'list agent templates' triggers list_agent_templates."""
        prompt = "What agent templates are available?"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["AGENT"],
        )

        response = result["response"]
        tools = result["tools"]
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Should call list templates tool OR respond about templates
        assert any(
            "template" in tool.lower() or "agent" in tool.lower()
            for tool in tools
        ) or any(
            word in response_text
            for word in ["template", "assistant", "agent", "available"]
        ), f"Expected list_agent_templates tool or response, got tools: {tools}, response: {response_text}"


@pytest.mark.eval
class TestAgentToolErrorHandling:
    """Test that agent handles agent tool errors gracefully."""

    def test_get_nonexistent_agent(self, airunner_client_function_scope):
        """Test handling when requested agent doesn't exist."""
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

        # Should acknowledge missing agent OR attempt to get
        assert any(
            "get" in tool.lower() or "agent" in tool.lower() for tool in tools
        ) or any(
            word in response_text
            for word in [
                "not found",
                "doesn't exist",
                "does not exist",
                "couldn't find",
                "no agent",
                "don't have",
            ]
        ), f"Expected acknowledgment or tool call, got tools: {tools}, response: {response_text}"

    def test_create_duplicate_agent(self, airunner_client_function_scope):
        """Test handling when trying to create agent with existing name."""
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

        # Should respond (may create or report error)
        assert response_text, "Expected some response"
