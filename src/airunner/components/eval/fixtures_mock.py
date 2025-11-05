"""
Mock fixtures for fast eval testing without real LLM calls.

These fixtures provide mocked LLM responses for testing tool triggering
logic without requiring a running server or real LLM inference.

Usage:
    @pytest.mark.fast
    def test_something(mock_airunner_client):
        # Client returns predefined responses instantly
        response = mock_airunner_client.generate("test prompt")
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List


class MockAIRunnerClient:
    """Mock client that returns predefined LLM responses."""

    def __init__(self):
        """Initialize mock client with default responses."""
        self.responses = {}
        self.call_count = 0
        self.last_request = None

    def set_response(
        self,
        prompt_pattern: str,
        response_text: str,
        tool_calls: List[Dict] = None,
        trajectory: List[Dict] = None,
    ):
        """
        Configure a response for prompts matching a pattern.

        Args:
            prompt_pattern: Pattern to match in prompt (case-insensitive)
            response_text: Text response to return
            tool_calls: Optional list of tool call dicts
            trajectory: Optional trajectory data
        """
        self.responses[prompt_pattern.lower()] = {
            "text": response_text,
            "tool_calls": tool_calls or [],
            "trajectory": trajectory or [],
            "nodes": [],
            "tools": [],
        }

    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        tool_categories: List[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Mock generate method that returns predefined responses.

        Args:
            prompt: User prompt
            max_tokens: Maximum tokens (ignored in mock)
            tool_categories: Tool categories (ignored in mock)
            **kwargs: Additional args (ignored in mock)

        Returns:
            Mock response dict
        """
        self.call_count += 1
        self.last_request = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "tool_categories": tool_categories,
            **kwargs,
        }

        # Find matching response
        prompt_lower = prompt.lower()
        for pattern, response in self.responses.items():
            if pattern in prompt_lower:
                return response

        # Default response if no match
        return {
            "text": "Mock response",
            "tool_calls": [],
            "trajectory": [],
            "nodes": [],
            "tools": [],
        }

    def generate_batch(
        self,
        prompts: List[str],
        max_tokens: int = 500,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Mock batch generation.

        Args:
            prompts: List of prompts
            max_tokens: Maximum tokens per response
            **kwargs: Additional arguments

        Returns:
            List of mock responses
        """
        return [
            self.generate(prompt, max_tokens=max_tokens, **kwargs)
            for prompt in prompts
        ]


@pytest.fixture
def mock_airunner_client() -> MockAIRunnerClient:
    """
    Provide a mock AI Runner client for fast testing.

    This fixture returns a MockAIRunnerClient that:
    - Returns responses instantly (no real LLM calls)
    - Can be configured with predefined responses
    - Tracks calls for verification

    Example:
        def test_agent_creation(mock_airunner_client):
            # Configure expected response
            mock_airunner_client.set_response(
                "create agent",
                "I've created the agent named Helper",
                tool_calls=[{"tool": "create_agent", "args": {...}}]
            )

            # Test uses the mock
            result = track_trajectory_sync(
                mock_airunner_client,
                "Create an agent named Helper"
            )
            assert "created" in result["response"].lower()
    """
    return MockAIRunnerClient()


@pytest.fixture
def mock_airunner_client_with_agent_responses(
    mock_airunner_client,
) -> MockAIRunnerClient:
    """
    Mock client preconfigured with agent-related responses.

    Automatically sets up responses for:
    - Agent creation
    - Agent listing
    - Agent retrieval
    - Agent configuration

    Example:
        def test_create_agent(mock_airunner_client_with_agent_responses):
            result = track_trajectory_sync(
                mock_airunner_client_with_agent_responses,
                "Create an agent named Helper"
            )
            assert "Helper" in result["response"]
    """
    # Agent creation
    mock_airunner_client.set_response(
        "create",
        "I've created a new agent named Helper to assist with coding tasks.",
        tool_calls=[
            {
                "tool": "create_agent",
                "args": {
                    "name": "Helper",
                    "description": "coding tasks",
                },
            }
        ],
    )

    # Agent listing
    mock_airunner_client.set_response(
        "list",
        "Here are your agents: Helper, Assistant, Researcher",
        tool_calls=[{"tool": "list_agents", "args": {}}],
    )

    # Agent retrieval
    mock_airunner_client.set_response(
        "get",
        "The agent Helper is configured to assist with coding tasks.",
        tool_calls=[{"tool": "get_agent", "args": {"agent_id": 1}}],
    )

    # Agent configuration
    mock_airunner_client.set_response(
        "configure",
        "I've updated the agent configuration.",
        tool_calls=[
            {
                "tool": "configure_agent",
                "args": {"agent_id": 1, "config": {}},
            }
        ],
    )

    return mock_airunner_client
