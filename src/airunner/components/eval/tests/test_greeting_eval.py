"""Eval tests for greeting and conversational responses without tool calls.

Tests that the LLM can handle simple greetings and conversations naturally
without hallucinating tool calls.
"""

import pytest
from airunner.components.eval.utils.tracking import track_trajectory_sync


class TestGreetingEval:
    """Test greeting and conversational behavior."""

    @pytest.mark.eval
    def test_simple_greeting(self, airunner_client_function_scope):
        """Test that 'Hello' gets a conversational response without tool calls."""
        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt="Hello",
            max_tokens=100,
        )
        
        response = result["response"].lower()
        tools = result.get("tools", [])
        
        assert any(
            greeting in response
            for greeting in ["hello", "hi", "hey", "greetings"]
        ), f"Expected greeting response, got: {result['response']}"
        
        assert len(tools) == 0, f"Expected no tool calls for greeting, got: {tools}"

    @pytest.mark.eval
    def test_how_are_you(self, airunner_client_function_scope):
        """Test that 'How are you?' gets a conversational response."""
        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt="How are you?",
            max_tokens=100,
        )
        
        response = result["response"].lower()
        tools = result.get("tools", [])
        
        assert len(response) > 0, "Expected a response"
        assert len(tools) == 0, f"Expected no tool calls for 'how are you', got: {tools}"

    @pytest.mark.eval
    def test_simple_question(self, airunner_client_function_scope):
        """Test that a simple question gets answered without tool calls."""
        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt="What can you do?",
            max_tokens=200,
        )
        
        response = result["response"].lower()
        tools = result.get("tools", [])
        
        assert len(response) > 10, "Expected substantive response"
        assert len(tools) == 0, f"Expected no tool calls for 'what can you do', got: {tools}"

    @pytest.mark.eval
    def test_conversational_followup(self, airunner_client_function_scope):
        """Test that conversational follow-ups work without tools."""
        # Initial greeting
        track_trajectory_sync(
            airunner_client_function_scope,
            prompt="Hello",
            max_tokens=100,
        )
        
        # Follow-up
        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt="Thanks! That's helpful.",
            max_tokens=100,
        )
        
        response = result["response"].lower()
        tools = result.get("tools", [])
        
        assert len(response) > 0, "Expected a response"
        assert len(tools) == 0, f"Expected no tool calls for acknowledgment, got: {tools}"
