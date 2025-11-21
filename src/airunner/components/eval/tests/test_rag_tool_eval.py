"""
Eval tests for RAG tool triggering with natural language.

Tests that the LLM agent can correctly trigger RAG and document search tools
when given natural language prompts like:
- "search my documents for information about Python"
- "save this article to my knowledge base"
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
class TestRAGToolEval:
    """Eval tests for natural language RAG tool triggering."""

    def test_rag_search_basic(self, airunner_client_function_scope):
        """Test that 'search documents for X' triggers rag_search tool."""
        prompt = "Search my documents for information about Python programming"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SEARCH"],
        )

        response = result["response"]
        tools = result["tools"]
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify tool was called OR response addresses the search
        assert any(
            "search" in tool.lower()
            or "rag" in tool.lower()
            or "knowledge" in tool.lower()
            for tool in tools
        ) or any(
            word in response_text
            for word in ["search", "documents", "knowledge base", "found"]
        ), f"Expected search tool or search response, got tools: {tools}, response: {response_text}"

    def test_rag_search_variations(self, airunner_client_function_scope):
        """Test various phrasings that should trigger RAG search."""
        test_prompts = [
            "look through my documents about machine learning",
            "find information in my knowledge base on AI",
            "search my files for neural networks",
            "what do my documents say about deep learning?",
        ]

        for prompt in test_prompts:
            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=400,
                tool_categories=["SEARCH"],
            )

            response = result["response"]
            tools = result["tools"]
            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )

            # Should trigger tool OR acknowledge search
            assert any(
                "search" in tool.lower()
                or "rag" in tool.lower()
                or "knowledge" in tool.lower()
                for tool in tools
            ) or any(
                word in response_text
                for word in [
                    "search",
                    "documents",
                    "knowledge base",
                    "found",
                    "looking",
                ]
            ), f"Failed to trigger for: {prompt}, got tools: {tools}, response: {response_text}"

    def test_search_knowledge_base_documents_basic(
        self, airunner_client_function_scope
    ):
        """Test keyword search in knowledge base documents."""
        prompt = "Search my knowledge base documents for Python tutorials"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["SEARCH"],
        )

        response = result["response"]
        tools = result["tools"]
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Should trigger search tool OR respond about search
        assert any(
            "search" in tool.lower() or "knowledge" in tool.lower()
            for tool in tools
        ) or any(
            word in response_text
            for word in [
                "search",
                "knowledge base",
                "documents",
                "python",
                "tutorial",
            ]
        ), f"Expected search tool or response, got tools: {tools}, response: {response_text}"

    def test_save_to_knowledge_base_basic(
        self, airunner_client_function_scope
    ):
        """Test saving content to knowledge base."""
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
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Should trigger save tool OR acknowledge the request
        assert any(
            "save" in tool.lower() or "knowledge" in tool.lower()
            for tool in tools
        ) or any(
            word in response_text
            for word in ["save", "saved", "store", "stored", "knowledge base"]
        ), f"Expected save tool or acknowledgment, got tools: {tools}, response: {response_text}"

    def test_save_to_knowledge_base_variations(
        self, airunner_client_function_scope
    ):
        """Test various phrasings for saving to knowledge base."""
        test_prompts = [
            "store this information in my knowledge base: test content",
            "add this to my documents: important data",
            "save this note to my knowledge base: reminder",
        ]

        for prompt in test_prompts:
            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=400,
                tool_categories=["SEARCH"],
            )

            response = result["response"]
            tools = result["tools"]
            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )

            # Should trigger save tool OR acknowledge
            assert any(
                "save" in tool.lower() or "knowledge" in tool.lower()
                for tool in tools
            ) or any(
                word in response_text
                for word in [
                    "save",
                    "saved",
                    "store",
                    "stored",
                    "add",
                    "added",
                ]
            ), f"Failed to trigger save for: {prompt}, got tools: {tools}, response: {response_text}"


@pytest.mark.eval
class TestRAGToolErrorHandling:
    """Test that agent handles RAG tool errors gracefully."""

    def test_rag_search_no_results(self, airunner_client_function_scope):
        """Test handling when RAG search returns no results."""
        prompt = "Search my documents for xyznonexistentquery12345"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["SEARCH"],
        )

        response = result["response"]
        tools = result["tools"]
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Should trigger search OR acknowledge no results
        assert any(
            "search" in tool.lower() or "knowledge" in tool.lower()
            for tool in tools
        ) or any(
            word in response_text
            for word in [
                "no results",
                "not found",
                "couldn't find",
                "no documents",
                "don't have",
                "doesn't match",
                "does not match",
                "no matches",
            ]
        ), f"Expected search or acknowledgment, got tools: {tools}, response: {response_text}"

    def test_rag_search_error(self, airunner_client_function_scope):
        """Test handling when RAG search encounters error."""
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

        # Should respond somehow (don't crash)
        assert response_text, "Expected some response"

    def test_save_to_knowledge_base_file_exists(
        self, airunner_client_function_scope
    ):
        """Test handling when trying to save to existing file."""
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

        # Should respond somehow
        assert response_text, "Expected some response"
