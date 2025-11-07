"""
Eval tests for knowledge tool triggering with natural language.

Tests that the LLM agent can correctly trigger knowledge management tools
when given natural language prompts like:
- "remember that Python is a programming language"
- "what do you know about machine learning?"
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
class TestKnowledgeToolEval:
    """Eval tests for natural language knowledge tool triggering."""

    def test_record_knowledge_basic(self, airunner_client_function_scope):
        """Test that 'remember that X' triggers record_knowledge tool."""
        prompt = "Remember that my favorite coffee shop is called Blue Moon Cafe on Elm Street"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=400,
            tool_categories=["KNOWLEDGE"],
        )

        response = result["response"]
        tools = result["tools"]
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Verify trajectory includes knowledge tool OR acknowledges the request
        assert any(
            "knowledge" in tool.lower() or "record" in tool.lower()
            for tool in tools
        ) or any(
            word in response_text
            for word in [
                "noted",
                "remembered",
                "stored",
                "recorded",
                "remember",
                "blue moon",
                "coffee",
            ]
        ), f"Expected knowledge/record tool or acknowledgment, got tools: {tools}, response: {response_text}"

    def test_record_knowledge_variations(self, airunner_client_function_scope):
        """Test various phrasings that should trigger knowledge recording."""
        test_prompts = [
            "note that my dentist appointment is next Tuesday at 3pm",
            "remember this fact: my car registration expires in March 2026",
            "I want you to know that my gym locker number is 42",
            "store this knowledge: my favorite pizza topping is pineapple and jalapeño",
        ]

        for prompt in test_prompts:
            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=400,
                tool_categories=["KNOWLEDGE"],
            )

            response = result["response"]
            tools = result["tools"]
            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )

            # Should trigger tool OR acknowledge in response
            assert any(
                "knowledge" in tool.lower() or "record" in tool.lower()
                for tool in tools
            ) or any(
                word in response_text
                for word in [
                    "noted",
                    "remembered",
                    "stored",
                    "recorded",
                    "saved",
                ]
            ), f"Failed to trigger record for: {prompt}, got tools: {tools}, response: {response_text}"

    def test_recall_knowledge_basic(self, airunner_client_function_scope):
        """Test that 'what do you know about X?' triggers recall_knowledge."""
        prompt = "What do you remember about my favorite coffee shop?"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["KNOWLEDGE"],
        )

        response = result["response"]
        tools = result["tools"]
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Should trigger tool OR give a response
        assert any(
            "knowledge" in tool.lower()
            or "recall" in tool.lower()
            or "search" in tool.lower()
            for tool in tools
        ) or any(
            word in response_text
            for word in [
                "coffee",
                "blue moon",
                "don't know",
                "remember",
                "know",
            ]
        ), f"Expected recall tool or response, got tools: {tools}, response: {response_text}"

    def test_recall_knowledge_variations(self, airunner_client_function_scope):
        """Test various phrasings that should trigger knowledge recall."""
        test_prompts = [
            "tell me what you remember about my dentist appointment",
            "what knowledge do you have about my car registration?",
            "recall information about my gym locker",
            "do you know anything about my favorite pizza toppings?",
        ]

        for prompt in test_prompts:
            result = track_trajectory_sync(
                airunner_client_function_scope,
                prompt=prompt,
                max_tokens=400,
                tool_categories=["KNOWLEDGE"],
            )

            response = result["response"]
            tools = result["tools"]
            response_text = (
                response.lower()
                if isinstance(response, str)
                else response.get("text", "").lower()
            )

            # Should trigger tool OR give relevant response
            assert any(
                "knowledge" in tool.lower()
                or "recall" in tool.lower()
                or "search" in tool.lower()
                for tool in tools
            ) or any(
                word in response_text
                for word in ["know", "remember", "recall", "information"]
            ), f"Failed to trigger recall for: {prompt}, got tools: {tools}, response: {response_text}"

    def test_recall_knowledge_by_category_basic(
        self, airunner_client_function_scope
    ):
        """Test recall by category."""
        prompt = "What personal appointments knowledge do you have?"

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            tool_categories=["KNOWLEDGE"],
        )

        response = result["response"]
        tools = result["tools"]
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )

        # Should trigger tool OR give relevant response
        assert any(
            "knowledge" in tool.lower()
            or "recall" in tool.lower()
            or "category" in tool.lower()
            for tool in tools
        ) or any(
            word in response_text
            for word in [
                "appointment",
                "personal",
                "knowledge",
                "don't have",
                "know",
            ]
        ), f"Expected knowledge tool or response, got tools: {tools}, response: {response_text}"

    def test_record_and_recall_workflow(self, airunner_client_function_scope):
        """Test workflow: record knowledge, then recall it."""
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

        record_text = (
            record_result["response"].lower()
            if isinstance(record_result["response"], str)
            else record_result["response"].get("text", "").lower()
        )

        # Should either call tool or acknowledge
        assert any(
            "knowledge" in tool.lower() or "record" in tool.lower()
            for tool in record_result["tools"]
        ) or any(
            word in record_text
            for word in ["noted", "remembered", "stored", "recorded"]
        ), f"Failed to record, got tools: {record_result['tools']}, response: {record_text}"

        # Then recall it
        recall_prompt = "What do you know about neural networks?"
        recall_result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=recall_prompt,
            max_tokens=400,
            tool_categories=["KNOWLEDGE"],
        )

        recall_text = (
            recall_result["response"].lower()
            if isinstance(recall_result["response"], str)
            else recall_result["response"].get("text", "").lower()
        )

        # Should either call tool or give response about neural networks
        assert any(
            "knowledge" in tool.lower()
            or "recall" in tool.lower()
            or "search" in tool.lower()
            for tool in recall_result["tools"]
        ) or any(
            word in recall_text
            for word in ["neural", "network", "deep learning", "know"]
        ), f"Failed to recall, got tools: {recall_result['tools']}, response: {recall_text}"


@pytest.mark.eval
class TestKnowledgeToolErrorHandling:
    """Test that agent handles knowledge tool errors gracefully."""

    def test_recall_no_knowledge(self, airunner_client_function_scope):
        """Test handling when no knowledge is found."""
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

        # Should acknowledge no knowledge found OR attempt to search
        assert any(
            "knowledge" in tool.lower()
            or "recall" in tool.lower()
            or "search" in tool.lower()
            for tool in tools
        ) or any(
            word in response_text
            for word in [
                "don't know",
                "no knowledge",
                "not found",
                "don't have",
                "couldn't",
                "couldn't find",
            ]
        ), f"Expected acknowledgment or tool call, got tools: {tools}, response: {response_text}"

    def test_record_knowledge_error(self, airunner_client_function_scope):
        """Test handling when recording knowledge fails."""
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

        # Should either call tool or acknowledge
        # This test just verifies the system doesn't crash
        assert response_text, "Expected some response"

    def test_recall_by_invalid_category(self, airunner_client_function_scope):
        """Test handling when recalling by invalid category."""
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
        assert response_text, "Expected some response"
