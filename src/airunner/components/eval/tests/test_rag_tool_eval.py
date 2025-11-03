"""
Eval tests for RAG tool triggering with natural language.

Tests that the LLM agent can correctly trigger RAG and document search tools
when given natural language prompts like:
- "search my documents for information about Python"
- "save this article to my knowledge base"
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
class TestRAGToolEval:
    """Eval tests for natural language RAG tool triggering."""

    @patch("airunner.components.llm.tools.rag_tools.rag_manager")
    def test_rag_search_basic(
        self, mock_rag_manager, airunner_client_function_scope
    ):
        """Test that 'search documents for X' triggers rag_search tool."""
        # Mock search results
        mock_rag_manager.search.return_value = [
            {"content": "Python is a programming language", "score": 0.95},
            {"content": "Python has great libraries", "score": 0.87},
        ]

        prompt = "Search my documents for information about Python programming"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SEARCH"],
        )

        response = result["response"]
        trajectory = result["trajectory"]
        tools = result["tools"]

        # Verify search was called
        assert mock_rag_manager.search.called
        call_args = mock_rag_manager.search.call_args[0]
        query = call_args[0].lower()
        assert "python" in query

        # Verify trajectory includes rag_search tool
        expected_trajectory = ["model", "rag_search", "model"]
        score = trajectory_subsequence(
            result, {"trajectory": expected_trajectory}
        )
        assert (
            score >= 0.66
        ), f"Expected rag_search in trajectory, got: {trajectory}"

        # Verify rag_search tool was used
        assert (
            "rag_search" in tools
        ), f"Expected rag_search in tools, got: {tools}"

        # Response should mention search results
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert (
            "python" in response_text
            or "programming" in response_text
            or "language" in response_text
        )

    @patch("airunner.components.llm.tools.rag_tools.rag_manager")
    def test_rag_search_variations(
        self, mock_rag_manager, airunner_client_function_scope
    ):
        """Test various phrasings that should trigger RAG search."""
        mock_rag_manager.search.return_value = [
            {"content": "Relevant content", "score": 0.9}
        ]

        test_prompts = [
            "look through my documents about machine learning",
            "find information in my knowledge base on AI",
            "search my files for neural networks",
            "what do my documents say about deep learning?",
        ]

        for prompt in test_prompts:
            mock_rag_manager.reset_mock()

            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=400,
                tool_categories=["SEARCH"],
            )

            response = result["response"]
            tools = result["tools"]

            # Should attempt RAG search
            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )
            assert (
                mock_rag_manager.search.called or "search" in response_text
            ), f"Failed to trigger RAG search for: {prompt}"

            # Verify rag_search tool was used
            assert (
                "rag_search" in tools
            ), f"Expected rag_search for prompt: {prompt}, got tools: {tools}"

    @patch("airunner.components.llm.tools.rag_tools.session_scope")
    def test_search_knowledge_base_documents_basic(
        self, mock_session_scope, airunner_client_function_scope
    ):
        """Test keyword search in knowledge base documents."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query

        mock_doc = Mock()
        mock_doc.name = "Python Tutorial.pdf"
        mock_doc.content = "Learn Python programming step by step"
        mock_doc.category = "tutorial"
        mock_query.all.return_value = [mock_doc]

        mock_session_scope.return_value.__enter__.return_value = mock_session

        prompt = "Search my knowledge base documents for Python tutorials"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SEARCH"],
        )

        response = result["response"]
        result["trajectory"]
        tools = result["tools"]

        # Verify document search was performed
        assert mock_session.query.called

        # Verify trajectory includes search tool
        assert (
            "search" in " ".join(tools).lower()
        ), f"Expected search tool in tools, got: {tools}"

        # Response should mention found documents
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert (
            "python" in response_text
            or "tutorial" in response_text
            or "document" in response_text
        )

    @patch("airunner.components.llm.tools.rag_tools.Document")
    @patch("airunner.components.llm.tools.rag_tools.session_scope")
    @patch("airunner.components.llm.tools.rag_tools.os.path.exists")
    @patch("airunner.components.llm.tools.rag_tools.builtins.open")
    def test_save_to_knowledge_base_basic(
        self,
        mock_open,
        mock_exists,
        mock_session_scope,
        mock_document,
        airunner_client_function_scope,
    ):
        """Test saving content to knowledge base."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_exists.return_value = False

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        prompt = (
            "Save this article about AI to my knowledge base: "
            "Artificial Intelligence is transforming technology"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SEARCH"],
        )

        response = result["response"]
        tools = result["tools"]

        # Verify save was attempted
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert (
            mock_document.called
            or mock_open.called
            or "saved" in response_text
            or "knowledge base" in response_text
        )

        # Verify save tool was used
        assert any(
            "save" in tool.lower() or "knowledge" in tool.lower()
            for tool in tools
        ), f"Expected save/knowledge tool in tools, got: {tools}"

    @patch("airunner.components.llm.tools.rag_tools.Document")
    @patch("airunner.components.llm.tools.rag_tools.session_scope")
    @patch("airunner.components.llm.tools.rag_tools.os.path.exists")
    @patch("airunner.components.llm.tools.rag_tools.builtins.open")
    def test_save_to_knowledge_base_variations(
        self,
        mock_open,
        mock_exists,
        mock_session_scope,
        mock_document,
        airunner_client_function_scope,
    ):
        """Test various phrasings for saving to knowledge base."""
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_exists.return_value = False
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        test_prompts = [
            "store this information in my knowledge base: test content",
            "add this to my documents: important data",
            "save this note to my knowledge base: reminder",
        ]

        for prompt in test_prompts:
            mock_document.reset_mock()
            mock_open.reset_mock()

            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=400,
                tool_categories=["SEARCH"],
            )

            response = result["response"]
            tools = result["tools"]

            # Should attempt to save
            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )
            assert (
                mock_document.called
                or mock_open.called
                or "saved" in response_text
                or "stored" in response_text
            ), f"Failed to trigger save for: {prompt}"

            # Verify save tool was used
            assert any(
                "save" in tool.lower() or "knowledge" in tool.lower()
                for tool in tools
            ), f"Expected save/knowledge tool for prompt: {prompt}, got tools: {tools}"


@pytest.mark.eval
class TestRAGToolErrorHandling:
    """Test that agent handles RAG tool errors gracefully."""

    @patch("airunner.components.llm.tools.rag_tools.rag_manager")
    def test_rag_search_no_results(
        self, mock_rag_manager, airunner_client_function_scope
    ):
        """Test handling when RAG search returns no results."""
        mock_rag_manager.search.return_value = []

        prompt = "Search my documents for xyznonexistentquery12345"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["SEARCH"],
        )

        response = result["response"]
        result["tools"]

        # Should still call search
        assert mock_rag_manager.search.called

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        # Should acknowledge no results
        assert (
            "no results" in response_text
            or "not found" in response_text
            or "couldn't find" in response_text
            or "no documents" in response_text
        )

    @patch("airunner.components.llm.tools.rag_tools.rag_manager")
    def test_rag_search_error(
        self, mock_rag_manager, airunner_client_function_scope
    ):
        """Test handling when RAG search encounters error."""
        mock_rag_manager.search.side_effect = Exception("Search failed")

        prompt = "Search my documents for Python"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["SEARCH"],
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
            or "failed" in response_text
        )

    @patch("airunner.components.llm.tools.rag_tools.Document")
    @patch("airunner.components.llm.tools.rag_tools.session_scope")
    @patch("airunner.components.llm.tools.rag_tools.os.path.exists")
    def test_save_to_knowledge_base_file_exists(
        self,
        mock_exists,
        mock_session_scope,
        mock_document,
        airunner_client_function_scope,
    ):
        """Test handling when trying to save to existing file."""
        mock_exists.return_value = True

        prompt = "Save this to my knowledge base: test content"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["SEARCH"],
        )

        response = result["response"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        # Should handle gracefully (either save with new name or acknowledge)
        assert "saved" in response_text or "already exists" in response_text
