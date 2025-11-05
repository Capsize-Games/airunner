"""
Eval tests for Research Mode with natural language prompts.

Tests that the mode-based routing correctly identifies research intent
and routes to the ResearchAgent which uses research-specific tools like:
- synthesize_sources()
- cite_sources()
- organize_research()
- extract_key_points()
- compare_sources()
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
class TestResearchModeEval:
    """Eval tests for Research Mode natural language triggering."""

    def test_synthesize_sources_basic(
        self,
        airunner_client_function_scope,
    ):
        """Test that source synthesis request routes to research mode."""
        prompt = (
            "Synthesize information from these sources: "
            "Source 1 says AI is transforming healthcare. "
            "Source 2 mentions AI diagnostic tools. "
            "Combine these findings."
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response synthesizes the sources
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in [
                "ai",
                "healthcare",
                "diagnostic",
                "transform",
                "synthesis",
            ]
        ), f"Response doesn't synthesize sources: {response_text}"

        # Verify synthesize_sources tool was used
        assert trajectory_contains(
            result, "synthesize_sources"
        ), f"Expected synthesize_sources tool, got: {tools}"

    def test_citation_formatting(
        self,
        airunner_client_function_scope,
    ):
        """Test that citation requests route to research mode."""
        prompt = (
            "Format a citation in APA style for: "
            "Smith, J. (2023). Machine Learning Basics. "
            "Tech Publishers."
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response provides citation
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in ["smith", "2023", "apa", "citation"]
        ), f"Response doesn't provide citation: {response_text}"

        # Verify cite_sources tool was used
        assert trajectory_contains(
            result, "cite_sources"
        ), f"Expected cite_sources tool, got: {tools}"

    def test_organize_research(
        self,
        airunner_client_function_scope,
    ):
        """Test that research organization request routes to research mode."""
        prompt = (
            "Organize these research findings: "
            "Finding 1: Climate change affects crops. "
            "Finding 2: Temperature rise impacts yield. "
            "Finding 3: Adaptation strategies exist."
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response organizes findings
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in [
                "climate",
                "crops",
                "yield",
                "adaptation",
                "organize",
            ]
        ), f"Response doesn't organize findings: {response_text}"

        # Verify organize_research tool was used
        assert trajectory_contains(
            result, "organize_research"
        ), f"Expected organize_research tool, got: {tools}"

    def test_extract_key_points(
        self,
        airunner_client_function_scope,
    ):
        """Test that key point extraction routes to research mode."""
        prompt = (
            "Extract the key points from this text: "
            "Quantum computing leverages quantum mechanics to process "
            "information. It uses qubits that can exist in superposition. "
            "This enables parallel processing of multiple states."
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response extracts key points
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in [
                "quantum",
                "qubits",
                "superposition",
                "key points",
                "main ideas",
            ]
        ), f"Response doesn't extract key points: {response_text}"

        # Verify extract_key_points tool was used
        assert trajectory_contains(
            result, "extract_key_points"
        ), f"Expected extract_key_points tool, got: {tools}"

    def test_compare_sources(
        self,
        airunner_client_function_scope,
    ):
        """Test that source comparison routes to research mode."""
        prompt = (
            "Compare these two sources: "
            "Source A claims renewable energy is cost-effective. "
            "Source B argues it's still expensive."
        )

        result = track_trajectory_sync(
            airunner_client_function_scope,
            prompt=prompt,
            max_tokens=500,
            use_mode_routing=True,
        )

        response = result["response"]
        tools = result["tools"]

        # Verify response compares sources
        response_text = (
            response.lower()
            if isinstance(response, str)
            else response.get("text", "").lower()
        )
        assert any(
            keyword in response_text
            for keyword in [
                "renewable",
                "cost",
                "expensive",
                "compare",
                "differ",
            ]
        ), f"Response doesn't compare sources: {response_text}"

        # Verify compare_sources tool was used
        assert trajectory_contains(
            result, "compare_sources"
        ), f"Expected compare_sources tool, got: {tools}"

    def test_research_mode_trajectory_efficiency(
        self,
        airunner_client_function_scope,
    ):
        """Test that research mode uses efficient tool paths."""
        prompt = (
            "Synthesize and cite these sources: "
            "Source 1 (Author 2023): Topic A. "
            "Source 2 (Writer 2024): Topic B."
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

        # Verify appropriate research tools used
        research_tools_used = [
            t
            for t in tools
            if t
            in [
                "synthesize_sources",
                "cite_sources",
                "organize_research",
                "extract_key_points",
                "compare_sources",
            ]
        ]
        assert len(research_tools_used) > 0, f"No research tools used: {tools}"
