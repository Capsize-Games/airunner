"""
Eval tests for knowledge tool triggering with natural language.

Tests that the LLM agent can correctly trigger knowledge management tools
when given natural language prompts like:
- "remember that Python is a programming language"
- "what do you know about machine learning?"
"""

import pytest
import logging
from unittest.mock import patch, Mock
from airunner.components.eval.utils.tracking import track_trajectory_sync

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.timeout(60),
]


@pytest.mark.eval
class TestKnowledgeToolEval:
    """Eval tests for natural language knowledge tool triggering."""

    @patch(
        "airunner.components.knowledge.knowledge_memory_manager.KnowledgeMemoryManager"
    )
    def test_record_knowledge_basic(
        self, mock_knowledge_manager, airunner_client_function_scope
    ):
        """Test that 'remember that X' triggers record_knowledge tool."""
        mock_manager_instance = Mock()
        mock_knowledge_manager.return_value = mock_manager_instance
        mock_manager_instance.add_fact.return_value = True

        prompt = "Remember that Python is a high-level programming language"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=400,
            tool_categories=["KNOWLEDGE"],
        )

        response = result["response"]
        tools = result["tools"]

        # Verify record was called
        assert (
            mock_manager_instance.add_fact.called
            or mock_knowledge_manager.called
        )

        # Verify trajectory includes knowledge tool
        assert any(
            "knowledge" in tool.lower() or "record" in tool.lower()
            for tool in tools
        ), f"Expected knowledge/record tool in tools, got: {tools}"

        # Response should acknowledge storage
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert (
            "remember" in response_text
            or "noted" in response_text
            or "recorded" in response_text
            or "stored" in response_text
            or "python" in response_text
        )

    @patch(
        "airunner.components.knowledge.knowledge_memory_manager.KnowledgeMemoryManager"
    )
    def test_record_knowledge_variations(
        self, mock_knowledge_manager, airunner_client_function_scope
    ):
        """Test various phrasings that should trigger knowledge recording."""
        mock_manager_instance = Mock()
        mock_knowledge_manager.return_value = mock_manager_instance
        mock_manager_instance.add_fact.return_value = True

        test_prompts = [
            "note that machine learning is a subset of AI",
            "remember this fact: neural networks learn from data",
            "I want you to know that deep learning uses multiple layers",
            "store this knowledge: AI can process natural language",
        ]

        for prompt in test_prompts:
            mock_manager_instance.reset_mock()
            mock_knowledge_manager.reset_mock()

            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=400,
                tool_categories=["KNOWLEDGE"],
            )

            response = result["response"]
            tools = result["tools"]

            # Should attempt to record knowledge
            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )
            assert (
                mock_manager_instance.add_fact.called
                or mock_knowledge_manager.called
                or any(
                    word in response_text
                    for word in ["noted", "remembered", "stored", "recorded"]
                )
            ), f"Failed to trigger record for: {prompt}"

            # Verify knowledge tool was used
            assert any(
                "knowledge" in tool.lower() or "record" in tool.lower()
                for tool in tools
            ), f"Expected knowledge/record tool for prompt: {prompt}, got tools: {tools}"

    @patch(
        "airunner.components.knowledge.knowledge_memory_manager.KnowledgeMemoryManager"
    )
    def test_recall_knowledge_basic(
        self, mock_knowledge_manager, airunner_client_function_scope
    ):
        """Test that 'what do you know about X?' triggers recall_knowledge."""
        mock_manager_instance = Mock()
        mock_knowledge_manager.return_value = mock_manager_instance
        mock_manager_instance.search_facts.return_value = [
            {
                "content": "Python is a high-level programming language",
                "category": "programming",
                "confidence": 0.95,
            }
        ]

        prompt = "What do you know about Python programming?"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["KNOWLEDGE"],
        )

        response = result["response"]
        tools = result["tools"]

        # Verify recall was called
        assert (
            mock_manager_instance.search_facts.called
            or mock_knowledge_manager.called
        )

        # Verify knowledge tool was used
        assert any(
            "knowledge" in tool.lower()
            or "recall" in tool.lower()
            or "search" in tool.lower()
            for tool in tools
        ), f"Expected knowledge/recall/search tool in tools, got: {tools}"

        # Response should contain recalled knowledge
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

    @patch(
        "airunner.components.knowledge.knowledge_memory_manager.KnowledgeMemoryManager"
    )
    def test_recall_knowledge_variations(
        self, mock_knowledge_manager, airunner_client_function_scope
    ):
        """Test various phrasings that should trigger knowledge recall."""
        mock_manager_instance = Mock()
        mock_knowledge_manager.return_value = mock_manager_instance
        mock_manager_instance.search_facts.return_value = [
            {"content": "AI fact", "category": "ai", "confidence": 0.9}
        ]

        test_prompts = [
            "tell me what you remember about machine learning",
            "what knowledge do you have about neural networks?",
            "recall information about deep learning",
            "do you know anything about artificial intelligence?",
        ]

        for prompt in test_prompts:
            mock_manager_instance.reset_mock()
            mock_knowledge_manager.reset_mock()

            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=400,
                tool_categories=["KNOWLEDGE"],
            )

            response = result["response"]
            tools = result["tools"]

            # Should attempt to recall knowledge
            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )
            assert (
                mock_manager_instance.search_facts.called
                or mock_knowledge_manager.called
                or any(
                    word in response_text
                    for word in ["know", "remember", "recall", "information"]
                )
            ), f"Failed to trigger recall for: {prompt}"

            # Verify knowledge tool was used
            assert any(
                "knowledge" in tool.lower()
                or "recall" in tool.lower()
                or "search" in tool.lower()
                for tool in tools
            ), f"Expected knowledge/recall/search tool for prompt: {prompt}, got tools: {tools}"

    @patch(
        "airunner.components.knowledge.knowledge_memory_manager.KnowledgeMemoryManager"
    )
    def test_recall_knowledge_by_category_basic(
        self, mock_knowledge_manager, airunner_client_function_scope
    ):
        """Test recall by category."""
        mock_manager_instance = Mock()
        mock_knowledge_manager.return_value = mock_manager_instance
        mock_manager_instance.get_facts_by_category.return_value = [
            {
                "content": "Python is versatile",
                "category": "programming",
                "confidence": 0.9,
            },
            {
                "content": "Python has many libraries",
                "category": "programming",
                "confidence": 0.85,
            },
        ]

        prompt = "What programming knowledge do you have?"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["KNOWLEDGE"],
        )

        response = result["response"]
        tools = result["tools"]

        # Verify category recall was attempted
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert (
            mock_manager_instance.get_facts_by_category.called
            or "programming" in response_text
            or "python" in response_text
        )

        # Verify knowledge tool was used
        assert any(
            "knowledge" in tool.lower()
            or "recall" in tool.lower()
            or "category" in tool.lower()
            for tool in tools
        ), f"Expected knowledge/recall/category tool in tools, got: {tools}"

    @patch(
        "airunner.components.knowledge.knowledge_memory_manager.KnowledgeMemoryManager"
    )
    def test_record_and_recall_workflow(
        self, mock_knowledge_manager, airunner_client_function_scope
    ):
        """Test workflow: record knowledge, then recall it."""
        mock_manager_instance = Mock()
        mock_knowledge_manager.return_value = mock_manager_instance
        mock_manager_instance.add_fact.return_value = True

        # First, record knowledge
        record_prompt = (
            "Remember that neural networks are used in deep learning"
        )
        record_result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=record_prompt,
            max_tokens=400,
            tool_categories=["KNOWLEDGE"],
        )

        # Simulate storage
        mock_manager_instance.search_facts.return_value = [
            {
                "content": "Neural networks are used in deep learning",
                "category": "ai",
                "confidence": 1.0,
            }
        ]

        # Then recall it
        recall_prompt = "What do you know about neural networks?"
        recall_result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=recall_prompt,
            max_tokens=400,
            tool_categories=["KNOWLEDGE"],
        )

        # Both operations should have interacted with knowledge manager
        assert (
            mock_manager_instance.add_fact.called
            or mock_manager_instance.search_facts.called
        )

        # Verify both record and recall tools were used
        assert any(
            "knowledge" in tool.lower() or "record" in tool.lower()
            for tool in record_result["tools"]
        ), f"Expected record tool in record step, got: {record_result['tools']}"
        assert any(
            "knowledge" in tool.lower()
            or "recall" in tool.lower()
            or "search" in tool.lower()
            for tool in recall_result["tools"]
        ), f"Expected recall tool in recall step, got: {recall_result['tools']}"

        # Recall response should mention neural networks
        recall_text = (
            recall_result["response"].lower()
            if isinstance(recall_result["response"], str)
            else recall_result["response"].get("text", "").lower()
        )
        assert (
            "neural" in recall_text
            or "network" in recall_text
            or "deep learning" in recall_text
        )


@pytest.mark.eval
class TestKnowledgeToolErrorHandling:
    """Test that agent handles knowledge tool errors gracefully."""

    @patch(
        "airunner.components.knowledge.knowledge_memory_manager.KnowledgeMemoryManager"
    )
    def test_recall_no_knowledge(
        self, mock_knowledge_manager, airunner_client_function_scope
    ):
        """Test handling when no knowledge is found."""
        mock_manager_instance = Mock()
        mock_knowledge_manager.return_value = mock_manager_instance
        mock_manager_instance.search_facts.return_value = []

        prompt = "What do you know about xyznonexistenttopic12345?"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["KNOWLEDGE"],
        )

        response = result["response"]
        tools = result["tools"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        # Should acknowledge no knowledge found
        assert (
            "don't know" in response_text
            or "no knowledge" in response_text
            or "not found" in response_text
            or "don't have" in response_text
        )

        # Should still attempt knowledge recall
        assert any(
            "knowledge" in tool.lower()
            or "recall" in tool.lower()
            or "search" in tool.lower()
            for tool in tools
        ), f"Expected knowledge/recall/search tool in tools, got: {tools}"

    @patch(
        "airunner.components.knowledge.knowledge_memory_manager.KnowledgeMemoryManager"
    )
    def test_record_knowledge_error(
        self, mock_knowledge_manager, airunner_client_function_scope
    ):
        """Test handling when recording knowledge fails."""
        mock_manager_instance = Mock()
        mock_knowledge_manager.return_value = mock_manager_instance
        mock_manager_instance.add_fact.side_effect = Exception(
            "Storage failed"
        )

        prompt = "Remember that test fact is important"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["KNOWLEDGE"],
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
            or "unable" in response_text
        )

    @patch(
        "airunner.components.knowledge.knowledge_memory_manager.KnowledgeMemoryManager"
    )
    def test_recall_by_invalid_category(
        self, mock_knowledge_manager, airunner_client_function_scope
    ):
        """Test handling when recalling by invalid category."""
        mock_manager_instance = Mock()
        mock_knowledge_manager.return_value = mock_manager_instance
        mock_manager_instance.get_facts_by_category.return_value = []

        prompt = "What do you know in the category of invalidcategory123?"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=300,
            tool_categories=["KNOWLEDGE"],
        )

        response = result["response"]

        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        # Should handle gracefully
        assert (
            "no" in response_text
            or "not found" in response_text
            or "don't have" in response_text
        )
