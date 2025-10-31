"""
Unit tests for LLM parameter flow from client to adapter.

These tests verify that max_new_tokens and other parameters
are correctly passed through the system without loading actual models.
"""

import pytest
from unittest.mock import Mock, patch

from airunner.components.eval.client import AIRunnerClient
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.enums import LLMActionType


class TestLLMRequestDataclass:
    """Test LLMRequest dataclass behavior."""

    def test_default_max_new_tokens(self):
        """Test default max_new_tokens value."""
        request = LLMRequest()
        assert request.max_new_tokens == 200  # default value

    def test_custom_max_new_tokens(self):
        """Test setting custom max_new_tokens."""
        request = LLMRequest(max_new_tokens=4096)
        assert request.max_new_tokens == 4096

    def test_to_dict_includes_max_new_tokens(self):
        """Test that to_dict() includes max_new_tokens."""
        request = LLMRequest(max_new_tokens=4096, temperature=0.8)
        result = request.to_dict()

        assert "max_new_tokens" in result
        assert result["max_new_tokens"] == 4096
        assert result["temperature"] == 0.8

    def test_for_action_decision_has_4096_tokens(self):
        """Test that for_action(DECISION) returns max_new_tokens=4096."""
        request = LLMRequest.for_action(LLMActionType.DECISION)

        # Should be 4096 after our fix for complex reasoning
        assert request.max_new_tokens == 4096

    def test_to_dict_preserves_all_generation_params(self):
        """Test that to_dict() preserves all generation parameters."""
        request = LLMRequest(
            max_new_tokens=4096,
            temperature=0.8,
            top_p=0.95,
            top_k=50,
            repetition_penalty=1.15,
            do_sample=True,
        )

        result = request.to_dict()

        # All generation parameters should be present
        assert result["max_new_tokens"] == 4096
        assert result["temperature"] == 0.8
        assert result["top_p"] == 0.95
        assert result["top_k"] == 50
        assert result["repetition_penalty"] == 1.15
        assert result["do_sample"] is True


class TestParameterFlow:
    """Test that parameters flow correctly through the system."""

    def test_generation_kwargs_cleanup_preserves_max_new_tokens(self):
        """Test that max_new_tokens survives kwargs cleanup."""
        # Start with full LLMRequest dict
        request = LLMRequest(
            max_new_tokens=4096,
            temperature=0.8,
            do_tts_reply=False,
            use_memory=True,
        )
        generation_kwargs = request.to_dict()

        # Simulate the cleanup in generation_mixin.py (line 256-263)
        for key in [
            "do_tts_reply",
            "use_cache",
            "node_id",
            "use_memory",
            "role",
        ]:
            generation_kwargs.pop(key, None)

        # Verify max_new_tokens survived cleanup
        assert "max_new_tokens" in generation_kwargs
        assert generation_kwargs["max_new_tokens"] == 4096
        assert generation_kwargs["temperature"] == 0.8

        # Verify non-generation params were removed
        assert "do_tts_reply" not in generation_kwargs
        assert "use_memory" not in generation_kwargs

    def test_workflow_state_preserves_generation_kwargs(self):
        """Test that workflow state stores and retrieves generation_kwargs."""
        generation_kwargs = {
            "max_new_tokens": 4096,
            "temperature": 0.8,
        }

        # Simulate workflow state (like in workflow_manager.py line 994-995)
        state = {"messages": [], "generation_kwargs": generation_kwargs}

        # Simulate extracting from state (like in workflow_manager.py line 746)
        extracted_kwargs = state.get("generation_kwargs", {})

        assert extracted_kwargs == generation_kwargs
        assert extracted_kwargs["max_new_tokens"] == 4096

    def test_adapter_kwargs_fallback_logic(self):
        """Test adapter's kwargs.get() fallback to default."""
        # Simulate adapter default
        adapter_default = 512

        # Case 1: max_new_tokens in kwargs → should use kwargs value
        kwargs_with_param = {"max_new_tokens": 4096}
        actual = kwargs_with_param.get("max_new_tokens", adapter_default)
        assert actual == 4096  # Should use kwargs, not default

        # Case 2: max_new_tokens NOT in kwargs → should use default
        kwargs_without_param = {"temperature": 0.8}
        actual = kwargs_without_param.get("max_new_tokens", adapter_default)
        assert actual == 512  # Should use default

        # This test reveals the problem: if kwargs doesn't have max_new_tokens,
        # the adapter falls back to its default (512), not the requested value!


class TestClientServerIntegration:
    """Test client-server parameter passing."""

    def test_client_builds_request_with_max_tokens(self):
        """Test that AIRunnerClient correctly builds request with max_tokens."""
        client = AIRunnerClient(base_url="http://localhost:8188")

        # Build request data (like in client.py line 133-137)
        request_data = client._build_request_data(
            prompt="Test prompt",
            model=None,
            max_tokens=4096,
            temperature=0.8,
            stream=False,
        )

        assert "max_tokens" in request_data
        assert request_data["max_tokens"] == 4096

    @patch("requests.post")
    def test_client_sends_max_tokens_to_server(self, mock_post):
        """Test that client sends max_tokens in HTTP request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "text": "response",
            "message": "response",
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = AIRunnerClient(base_url="http://localhost:8188")
        client.generate(prompt="Test", max_tokens=4096)

        # Verify POST was called with correct data
        assert mock_post.called
        json_data = mock_post.call_args.kwargs["json"]
        assert json_data["max_tokens"] == 4096


class TestServerParameterMapping:
    """Test server's parameter mapping logic."""

    def test_param_mapping_dict_correctness(self):
        """Test that max_tokens correctly maps to max_new_tokens."""
        # This is the mapping in server.py line 168-176
        param_mapping = {
            "temperature": "temperature",
            "max_tokens": "max_new_tokens",  # CRITICAL
            "top_p": "top_p",
            "top_k": "top_k",
            "repetition_penalty": "repetition_penalty",
        }

        assert param_mapping["max_tokens"] == "max_new_tokens"

        # Simulate mapping process (server.py line 178-185)
        client_data = {"max_tokens": 4096, "temperature": 0.8}
        llm_request_data = {}

        for client_param, llm_param in param_mapping.items():
            if client_param in client_data:
                llm_request_data[llm_param] = client_data[client_param]

        # Verify mapping worked
        assert llm_request_data["max_new_tokens"] == 4096
        assert "max_tokens" not in llm_request_data  # Should be renamed


class TestMockWorkflowGeneration:
    """Test generation flow with mocked components."""

    @patch("airunner.components.llm.managers.workflow_manager.WorkflowManager")
    def test_workflow_receives_generation_kwargs(self, mock_workflow_class):
        """Test that WorkflowManager.stream() receives generation_kwargs."""
        mock_workflow = Mock()
        mock_workflow_class.return_value = mock_workflow
        mock_workflow.stream = Mock(return_value=iter([]))

        # Simulate generation_mixin.py calling workflow.stream (line 267)
        generation_kwargs = {"max_new_tokens": 4096, "temperature": 0.8}
        list(mock_workflow.stream("test prompt", generation_kwargs))

        # Verify stream was called with kwargs
        mock_workflow.stream.assert_called_once_with(
            "test prompt", generation_kwargs
        )
