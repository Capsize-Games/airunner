"""
Eval tests for user data tool triggering with natural language.

Tests that the LLM agent can correctly trigger user data storage and retrieval
tools when given natural language prompts like:
- "remember that my favorite color is blue"
- "what's my email address?"
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
class TestUserDataToolEval:
    """Eval tests for natural language user data tool triggering."""

    @patch("airunner.components.llm.tools.user_data_tools.User")
    @patch("airunner.components.llm.tools.user_data_tools.session_scope")
    def test_store_user_data_basic(
        self, mock_session_scope, mock_user, airunner_client_function_scope
    ):
        """Test that 'remember X' triggers store_user_data tool."""
        # Mock database session and user
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_user_instance = Mock()
        mock_user.get_or_create.return_value = mock_user_instance

        prompt = "Remember that my favorite color is blue"

        # Track trajectory and response
        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["USER_DATA"],
        )

        response = result["response"]
        trajectory = result["trajectory"]
        tools = result["tools"]

        # Verify store tool was called
        assert mock_user.get_or_create.called

        # Verify trajectory includes user data tool
        expected_trajectory = ["model", "store_user_data", "model"]
        score = trajectory_subsequence(
            result, {"trajectory": expected_trajectory}
        )
        assert (
            score >= 0.66
        ), f"Expected store_user_data in trajectory, got: {trajectory}"

        # Verify store_user_data tool was used
        assert (
            "store_user_data" in tools
        ), f"Expected store_user_data in tools, got: {tools}"

        # Verify response acknowledges storage
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert (
            "remember" in response_text
            or "stored" in response_text
            or "saved" in response_text
            or "noted" in response_text
            or "blue" in response_text
        )

    @patch("airunner.components.llm.tools.user_data_tools.User")
    @patch("airunner.components.llm.tools.user_data_tools.session_scope")
    def test_store_user_data_variations(
        self, mock_session_scope, mock_user, airunner_client_function_scope
    ):
        """Test various phrasings that should trigger data storage."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_user_instance = Mock()
        mock_user.get_or_create.return_value = mock_user_instance

        test_prompts = [
            "save my email as user@example.com",
            "my phone number is 555-1234, remember that",
            "I want you to remember that I live in New York",
            "store this information: my birthday is January 1st",
        ]

        for prompt in test_prompts:
            mock_user.reset_mock()

            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=300,
                tool_categories=["USER_DATA"],
            )

            response = result["response"]
            tools = result["tools"]

            # Should attempt to store data
            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )
            assert mock_user.get_or_create.called or any(
                word in response_text
                for word in ["saved", "stored", "remembered", "noted"]
            ), f"Failed to trigger store for: {prompt}"

            # Verify store_user_data tool was used
            assert (
                "store_user_data" in tools
            ), f"Expected store_user_data for prompt: {prompt}, got tools: {tools}"

    @patch("airunner.components.llm.tools.user_data_tools.User")
    @patch("airunner.components.llm.tools.user_data_tools.session_scope")
    def test_get_user_data_basic(
        self, mock_session_scope, mock_user, airunner_client_function_scope
    ):
        """Test that 'what's my X?' triggers get_user_data tool."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_user_instance = Mock()
        mock_user_instance.email = "user@example.com"
        mock_user.get_or_create.return_value = mock_user_instance

        prompt = "What's my email address?"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["USER_DATA"],
        )

        response = result["response"]
        trajectory = result["trajectory"]
        tools = result["tools"]

        # Verify get tool was called
        assert mock_user.get_or_create.called

        # Verify trajectory includes user data tool
        expected_trajectory = ["model", "get_user_data", "model"]
        score = trajectory_subsequence(
            result, {"trajectory": expected_trajectory}
        )
        assert (
            score >= 0.66
        ), f"Expected get_user_data in trajectory, got: {trajectory}"

        # Verify get_user_data tool was used
        assert (
            "get_user_data" in tools
        ), f"Expected get_user_data in tools, got: {tools}"

        # Response should contain the email or acknowledge retrieval
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert "user@example.com" in response_text or "email" in response_text

    @patch("airunner.components.llm.tools.user_data_tools.User")
    @patch("airunner.components.llm.tools.user_data_tools.session_scope")
    def test_get_user_data_variations(
        self, mock_session_scope, mock_user, airunner_client_function_scope
    ):
        """Test various phrasings that should trigger data retrieval."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_user_instance = Mock()
        mock_user_instance.favorite_color = "blue"
        mock_user_instance.location = "New York"
        mock_user.get_or_create.return_value = mock_user_instance

        test_prompts = [
            "what is my favorite color?",
            "do you know where I live?",
            "tell me my location",
            "what information do you have about me?",
        ]

        for prompt in test_prompts:
            mock_user.reset_mock()

            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=300,
                tool_categories=["USER_DATA"],
            )

            response = result["response"]
            tools = result["tools"]

            # Should attempt to retrieve data
            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )
            assert mock_user.get_or_create.called or any(
                word in response_text
                for word in ["blue", "new york", "don't know", "information"]
            ), f"Failed to trigger get for: {prompt}"

            # Verify get_user_data tool was used
            assert (
                "get_user_data" in tools
            ), f"Expected get_user_data for prompt: {prompt}, got tools: {tools}"

    @patch("airunner.components.llm.tools.user_data_tools.User")
    @patch("airunner.components.llm.tools.user_data_tools.session_scope")
    def test_store_and_retrieve_workflow(
        self, mock_session_scope, mock_user, airunner_client_function_scope
    ):
        """Test workflow: store data, then retrieve it."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_user_instance = Mock()
        mock_user_instance.favorite_food = None
        mock_user.get_or_create.return_value = mock_user_instance

        # First, store data
        store_prompt = "Remember that my favorite food is pizza"
        store_result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=store_prompt,
            max_tokens=300,
            tool_categories=["USER_DATA"],
        )

        # Simulate storage
        mock_user_instance.favorite_food = "pizza"

        # Then retrieve it
        get_prompt = "What's my favorite food?"
        get_result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=get_prompt,
            max_tokens=300,
            tool_categories=["USER_DATA"],
        )

        # Both operations should have called User.get_or_create
        assert mock_user.get_or_create.call_count >= 2

        # Verify store then get in tools
        assert "store_user_data" in store_result["tools"]
        assert "get_user_data" in get_result["tools"]

        # Retrieve response should mention pizza
        get_text = (
            get_result["response"].lower()
            if isinstance(get_result["response"], str)
            else get_result["response"].get("text", "").lower()
        )
        assert "pizza" in get_text or "food" in get_text


@pytest.mark.eval
class TestUserDataToolErrorHandling:
    """Test that agent handles user data tool errors gracefully."""

    @patch("airunner.components.llm.tools.user_data_tools.User")
    @patch("airunner.components.llm.tools.user_data_tools.session_scope")
    def test_get_nonexistent_data(
        self, mock_session_scope, mock_user, airunner_client_function_scope
    ):
        """Test handling when requested data doesn't exist."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        mock_user_instance = Mock()
        # No attributes set - all None
        mock_user_instance.nonexistent_field = None
        mock_user.get_or_create.return_value = mock_user_instance

        prompt = "What's my favorite animal?"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["USER_DATA"],
        )

        response = result["response"]
        tools = result["tools"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        # Should acknowledge missing data
        assert (
            "don't have" in response_text
            or "not found" in response_text
            or "don't know" in response_text
            or "haven't" in response_text
        )

        # Should still attempt to get user data
        assert "get_user_data" in tools

    @patch("airunner.components.llm.tools.user_data_tools.User")
    @patch("airunner.components.llm.tools.user_data_tools.session_scope")
    def test_store_invalid_key(
        self, mock_session_scope, mock_user, airunner_client_function_scope
    ):
        """Test handling when trying to store with invalid key name."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_user.get_or_create.side_effect = AttributeError(
            "Invalid attribute"
        )

        prompt = "Remember that my 123invalid is test"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["USER_DATA"],
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
            or "couldn't" in response_text
            or "unable" in response_text
            or "invalid" in response_text
        )
