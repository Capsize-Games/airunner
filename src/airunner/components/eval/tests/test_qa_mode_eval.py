"""
Eval tests for QA Mode with natural language prompts.

Tests that the mode-based routing correctly identifies QA intent
and routes to the QAAgent which uses QA-specific tools like:
- verify_answer()
- score_answer_confidence()
- extract_answer_from_context()
- generate_clarifying_questions()
- rank_answer_candidates()
- identify_answer_type()
"""

import pytest
import logging
from airunner.components.eval.utils.tracking import track_trajectory_sync
from airunner.components.eval.utils.trajectory_evaluator import (
    trajectory_contains,
)

logger = logging.getLogger(__name__)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.timeout(60),
]


@pytest.mark.eval
class TestQAModeEval:
    """Eval tests for QA Mode natural language triggering."""

    def test_verify_answer_basic(
        self,
        airunner_client_function_scope,
    ):
        """Test that answer verification request routes to QA mode."""
        prompt = (
            "Verify if this answer is correct: "
            "Question: What is the capital of France? "
            "Answer: Paris"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response addresses verification
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in ["correct", "verified", "yes", "accurate", "paris"]
        ), f"Response doesn't verify answer: {response_text}"

        # Verify verify_answer tool was used
        assert trajectory_contains(
            result, "verify_answer"
        ), f"Expected verify_answer tool, got: {tools}"

    def test_confidence_scoring(
        self,
        airunner_client_function_scope,
    ):
        """Test that confidence scoring request routes to QA mode."""
        prompt = (
            "Score the confidence of this answer: "
            "Question: What year did WWII end? "
            "Answer: 1945"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response provides confidence score
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in ["confidence", "score", "high", "certain", "1945"]
        ), f"Response doesn't score confidence: {response_text}"

        # Verify score_answer_confidence tool was used
        assert trajectory_contains(
            result, "score_answer_confidence"
        ), f"Expected score_answer_confidence tool, got: {tools}"

    def test_extract_answer_from_context(
        self,
        airunner_client_function_scope,
    ):
        """Test that answer extraction routes to QA mode."""
        prompt = (
            "Extract the answer from this context: "
            "Context: The Eiffel Tower was completed in 1889 for the "
            "World's Fair. It stands 330 meters tall. "
            "Question: When was the Eiffel Tower completed?"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response extracts the answer
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in ["1889", "eighteen", "answer", "completed"]
        ), f"Response doesn't extract answer: {response_text}"

        # Verify extract_answer_from_context tool was used
        assert trajectory_contains(
            result, "extract_answer_from_context"
        ), f"Expected extract_answer_from_context tool, got: {tools}"

    def test_generate_clarifying_questions(
        self,
        airunner_client_function_scope,
    ):
        """Test that clarifying question generation routes to QA mode."""
        prompt = (
            "Generate clarifying questions for this ambiguous query: "
            "'Tell me about the revolution'"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response provides clarifying questions
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in [
                "which",
                "what",
                "french",
                "american",
                "industrial",
                "clarify",
            ]
        ), f"Response doesn't provide clarifying questions: {response_text}"

        # Verify generate_clarifying_questions tool was used
        assert trajectory_contains(
            result, "generate_clarifying_questions"
        ), f"Expected generate_clarifying_questions tool, got: {tools}"

    def test_rank_answer_candidates(
        self,
        airunner_client_function_scope,
    ):
        """Test that answer ranking routes to QA mode."""
        prompt = (
            "Rank these answer candidates: "
            "Question: What is photosynthesis? "
            "Candidate 1: A process plants use to make food. "
            "Candidate 2: When plants turn green. "
            "Candidate 3: The conversion of light energy to chemical energy."
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response ranks candidates
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in ["rank", "best", "candidate", "3", "accurate"]
        ), f"Response doesn't rank candidates: {response_text}"

        # Verify rank_answer_candidates tool was used
        assert trajectory_contains(
            result, "rank_answer_candidates"
        ), f"Expected rank_answer_candidates tool, got: {tools}"

    def test_identify_answer_type(
        self,
        airunner_client_function_scope,
    ):
        """Test that answer type identification routes to QA mode."""
        prompt = (
            "Identify the answer type for this question: "
            "'When did the Renaissance begin?'"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response identifies type
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in ["date", "time", "temporal", "when", "type"]
        ), f"Response doesn't identify type: {response_text}"

        # Verify identify_answer_type tool was used
        assert trajectory_contains(
            result, "identify_answer_type"
        ), f"Expected identify_answer_type tool, got: {tools}"

    def test_qa_mode_trajectory_efficiency(
        self,
        airunner_client_function_scope,
    ):
        """Test that QA mode uses efficient tool paths."""
        prompt = (
            "Extract and verify the answer: "
            "Context: Python was created by Guido van Rossum in 1991. "
            "Question: Who created Python?"
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        trajectory = result["trajectory"]
        tools = result["tools"]

        # Verify trajectory is efficient
        assert (
            len(trajectory) < 10
        ), f"Trajectory too long (inefficient): {trajectory}"

        # Verify appropriate QA tools used
        qa_tools_used = [
            t
            for t in tools
            if t
            in [
                "verify_answer",
                "score_answer_confidence",
                "extract_answer_from_context",
                "generate_clarifying_questions",
                "rank_answer_candidates",
                "identify_answer_type",
            ]
        ]
        assert len(qa_tools_used) > 0, f"No QA tools used: {tools}"
