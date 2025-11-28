"""Tests for the task complexity detector."""

import pytest

from airunner.components.llm.long_running.task_detector import (
    TaskType,
    TaskAnalysis,
    analyze_task,
    should_use_harness,
    _extract_comma_list,
)


class TestAnalyzeTask:
    """Test the analyze_task function."""

    def test_simple_greeting_no_harness(self):
        """Simple greetings should not trigger harness."""
        analysis = analyze_task("Hello, how are you?")
        assert analysis.task_type == TaskType.SIMPLE
        assert not analysis.should_use_harness
        assert analysis.confidence < 0.5

    def test_simple_question_no_harness(self):
        """Simple questions should not trigger harness."""
        analysis = analyze_task("What is the capital of France?")
        assert not analysis.should_use_harness

    def test_explicit_number_multi_research(self):
        """'Research 5 papers' should trigger harness."""
        analysis = analyze_task("Research 5 papers on quantum computing")
        assert analysis.should_use_harness
        assert analysis.task_type == TaskType.MULTI_RESEARCH
        assert len(analysis.detected_items) == 5
        assert analysis.confidence >= 0.8

    def test_explicit_number_features(self):
        """'Implement 3 features' should trigger harness."""
        analysis = analyze_task("Implement 3 features for the login system")
        assert analysis.should_use_harness
        assert len(analysis.detected_items) == 3
        assert analysis.confidence >= 0.8

    def test_comma_list_research(self):
        """Comma-separated list should trigger harness."""
        analysis = analyze_task(
            "Research machine learning, neural networks, and deep learning"
        )
        assert analysis.should_use_harness
        assert len(analysis.detected_items) >= 3

    def test_coding_project_keywords(self):
        """Multiple coding keywords should trigger harness."""
        analysis = analyze_task(
            "Refactor the authentication module and add unit tests"
        )
        assert analysis.should_use_harness
        assert analysis.task_type == TaskType.CODING_PROJECT

    def test_single_coding_keyword_low_confidence(self):
        """Single coding keyword should have lower confidence."""
        analysis = analyze_task("Implement a button")
        # Single keyword might not trigger harness
        assert analysis.confidence < 0.7

    def test_multi_step_keywords(self):
        """Multi-step keywords should trigger harness."""
        analysis = analyze_task(
            "First, set up the database, then create the API endpoints"
        )
        assert analysis.should_use_harness
        assert "Multi-step" in analysis.reason or analysis.task_type == TaskType.MULTI_STEP

    def test_complex_analysis_keywords(self):
        """Analysis keywords should trigger harness."""
        analysis = analyze_task(
            "Analyze and evaluate the performance of our caching system"
        )
        # Multiple analysis keywords
        assert analysis.confidence >= 0.5

    def test_write_multiple_papers(self):
        """Write multiple papers should trigger harness."""
        analysis = analyze_task("Write 3 research papers on AI ethics")
        assert analysis.should_use_harness
        assert len(analysis.detected_items) == 3

    def test_investigate_multiple(self):
        """Investigate multiple topics should trigger harness."""
        analysis = analyze_task("Investigate multiple approaches to caching")
        assert analysis.should_use_harness

    def test_numbered_list_detection(self):
        """Numbered lists should be detected."""
        analysis = analyze_task(
            "Do the following: 1. Create database 2. Add API 3. Write tests"
        )
        # Should detect the multi-item nature
        assert analysis.confidence >= 0.5


class TestExtractCommaList:
    """Test the comma list extraction helper."""

    def test_research_comma_list(self):
        """Extract items from 'research X, Y, and Z'."""
        items = _extract_comma_list("research cats, dogs, and birds")
        assert len(items) >= 3
        assert "cats" in items
        assert "dogs" in items
        assert "birds" in items

    def test_implement_comma_list(self):
        """Extract items from 'implement A, B, C'."""
        items = _extract_comma_list("implement login, signup, and logout")
        assert len(items) >= 3

    def test_no_list(self):
        """No list should return empty."""
        items = _extract_comma_list("hello world")
        assert items == []


class TestShouldUseHarness:
    """Test the should_use_harness convenience function."""

    def test_simple_returns_false_none(self):
        """Simple prompts return (False, None)."""
        use, analysis = should_use_harness("Hi there!")
        assert use is False
        assert analysis is None

    def test_complex_returns_true_analysis(self):
        """Complex prompts return (True, analysis)."""
        use, analysis = should_use_harness("Research 5 papers on AI")
        assert use is True
        assert analysis is not None
        assert analysis.should_use_harness


class TestTaskTypeDetection:
    """Test correct task type assignment."""

    def test_research_type(self):
        """Research tasks get MULTI_RESEARCH type."""
        analysis = analyze_task("Research and write about 3 historical events")
        if analysis.should_use_harness:
            assert analysis.task_type == TaskType.MULTI_RESEARCH

    def test_coding_type(self):
        """Coding tasks get CODING_PROJECT type."""
        analysis = analyze_task("Build and deploy a REST API with tests")
        if analysis.should_use_harness:
            assert analysis.task_type == TaskType.CODING_PROJECT

    def test_analysis_type(self):
        """Analysis tasks get COMPLEX_ANALYSIS type."""
        analysis = analyze_task(
            "Analyze and assess the security vulnerabilities comprehensively"
        )
        if analysis.should_use_harness:
            assert analysis.task_type in [
                TaskType.COMPLEX_ANALYSIS,
                TaskType.MULTI_STEP,
            ]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_prompt(self):
        """Empty prompt should not crash."""
        analysis = analyze_task("")
        assert not analysis.should_use_harness

    def test_very_long_prompt(self):
        """Very long prompts should work."""
        long_prompt = "Research " + "topic " * 100
        analysis = analyze_task(long_prompt)
        # Should not crash
        assert isinstance(analysis, TaskAnalysis)

    def test_special_characters(self):
        """Special characters should not crash."""
        analysis = analyze_task("Research @#$%^&*() topics!!!")
        assert isinstance(analysis, TaskAnalysis)

    def test_unicode(self):
        """Unicode should work."""
        analysis = analyze_task("Research 5 topics about 日本語")
        assert analysis.should_use_harness
        assert len(analysis.detected_items) == 5
