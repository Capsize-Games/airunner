"""
Unit tests for trajectory evaluation utilities.
"""

import pytest
from airunner.components.eval.utils.trajectory_evaluator import (
    trajectory_subsequence,
    trajectory_exact_match,
    trajectory_contains,
    trajectory_tool_usage,
    trajectory_efficiency_score,
)


class TestTrajectorySubsequence:
    """Tests for trajectory_subsequence evaluator."""

    def test_perfect_match(self):
        """Test perfect subsequence match."""
        outputs = {"trajectory": ["model", "tools", "search", "model"]}
        reference = {"trajectory": ["model", "tools", "search", "model"]}

        score = trajectory_subsequence(outputs, reference)
        assert score == 1.0

    def test_with_extra_steps(self):
        """Test subsequence with extra steps in between."""
        outputs = {
            "trajectory": ["model", "tools", "search", "tools", "rag", "model"]
        }
        reference = {"trajectory": ["model", "search", "model"]}

        score = trajectory_subsequence(outputs, reference)
        assert score == 1.0  # All expected steps found in order

    def test_missing_steps(self):
        """Test with missing expected steps."""
        outputs = {"trajectory": ["model", "model"]}
        reference = {"trajectory": ["model", "search", "model"]}

        score = trajectory_subsequence(outputs, reference)
        # First 'model' matches, 'search' not found, so only 1/3 steps found
        assert score == pytest.approx(1 / 3)

    def test_empty_actual(self):
        """Test with empty actual trajectory."""
        outputs = {"trajectory": []}
        reference = {"trajectory": ["model", "search"]}

        score = trajectory_subsequence(outputs, reference)
        assert score == 0.0

    def test_no_expected(self):
        """Test with no expected trajectory (automatic pass)."""
        outputs = {"trajectory": ["model", "search"]}
        reference = {}

        score = trajectory_subsequence(outputs, reference)
        assert score == 1.0

    def test_out_of_order(self):
        """Test with steps out of order."""
        outputs = {"trajectory": ["search", "model"]}
        reference = {"trajectory": ["model", "search"]}

        score = trajectory_subsequence(outputs, reference)
        assert score == 0.5  # Only 'search' matches (model comes after)


class TestTrajectoryExactMatch:
    """Tests for trajectory_exact_match evaluator."""

    def test_exact_match(self):
        """Test exact trajectory match."""
        outputs = {"trajectory": ["model", "tools", "search", "model"]}
        reference = {"trajectory": ["model", "tools", "search", "model"]}

        assert trajectory_exact_match(outputs, reference) is True

    def test_extra_step(self):
        """Test with extra step (not exact)."""
        outputs = {
            "trajectory": ["model", "tools", "search", "tools", "model"]
        }
        reference = {"trajectory": ["model", "tools", "search", "model"]}

        assert trajectory_exact_match(outputs, reference) is False

    def test_missing_step(self):
        """Test with missing step (not exact)."""
        outputs = {"trajectory": ["model", "search", "model"]}
        reference = {"trajectory": ["model", "tools", "search", "model"]}

        assert trajectory_exact_match(outputs, reference) is False

    def test_different_order(self):
        """Test with different order (not exact)."""
        outputs = {"trajectory": ["tools", "model", "search", "model"]}
        reference = {"trajectory": ["model", "tools", "search", "model"]}

        assert trajectory_exact_match(outputs, reference) is False

    def test_no_expected(self):
        """Test with no expected trajectory (automatic pass)."""
        outputs = {"trajectory": ["model", "search"]}
        reference = {}

        assert trajectory_exact_match(outputs, reference) is True


class TestTrajectoryContains:
    """Tests for trajectory_contains helper."""

    def test_contains_all(self):
        """Test when trajectory contains all required steps."""
        outputs = {"trajectory": ["model", "tools", "search", "rag", "model"]}
        required = ["search", "rag"]

        assert trajectory_contains(outputs, required) is True

    def test_contains_with_extras(self):
        """Test when trajectory has required plus extra steps."""
        outputs = {
            "trajectory": ["model", "tools", "search", "code", "rag", "model"]
        }
        required = ["search", "rag"]

        assert trajectory_contains(outputs, required) is True

    def test_missing_one(self):
        """Test when trajectory is missing one required step."""
        outputs = {"trajectory": ["model", "search", "model"]}
        required = ["search", "rag"]

        assert trajectory_contains(outputs, required) is False

    def test_empty_required(self):
        """Test with empty required list (should pass)."""
        outputs = {"trajectory": ["model", "search"]}
        required = []

        assert trajectory_contains(outputs, required) is True

    def test_empty_actual(self):
        """Test with empty actual trajectory."""
        outputs = {"trajectory": []}
        required = ["search"]

        assert trajectory_contains(outputs, required) is False


class TestTrajectoryToolUsage:
    """Tests for trajectory_tool_usage analyzer."""

    def test_count_tools(self):
        """Test counting tool usage."""
        outputs = {"trajectory": ["model", "search", "search", "rag", "model"]}

        counts = trajectory_tool_usage(outputs)
        assert counts == {"search": 2, "rag": 1}

    def test_with_tools_key(self):
        """Test using explicit tools list."""
        outputs = {
            "trajectory": ["model", "tools", "model"],
            "tools": ["search", "rag", "search"],
        }

        counts = trajectory_tool_usage(outputs)
        assert counts == {"search": 2, "rag": 1}

    def test_no_tools(self):
        """Test with trajectory containing no tools."""
        outputs = {"trajectory": ["model", "model"]}

        counts = trajectory_tool_usage(outputs)
        assert counts == {}

    def test_empty_trajectory(self):
        """Test with empty trajectory."""
        outputs = {"trajectory": []}

        counts = trajectory_tool_usage(outputs)
        assert counts == {}


class TestTrajectoryEfficiencyScore:
    """Tests for trajectory_efficiency_score evaluator."""

    def test_perfect_efficiency(self):
        """Test when trajectories are same length."""
        outputs = {"trajectory": ["model", "search", "model"]}
        reference = {"trajectory": ["model", "search", "model"]}

        score = trajectory_efficiency_score(outputs, reference)
        assert score == 1.0

    def test_longer_actual(self):
        """Test when actual is longer (less efficient)."""
        outputs = {"trajectory": ["model", "search", "search", "model"]}
        reference = {"trajectory": ["model", "search", "model"]}

        score = trajectory_efficiency_score(outputs, reference)
        assert score == 0.75  # 3/4

    def test_shorter_actual(self):
        """Test when actual is shorter (capped at 1.0)."""
        outputs = {"trajectory": ["model", "search"]}
        reference = {"trajectory": ["model", "search", "rag", "model"]}

        score = trajectory_efficiency_score(outputs, reference)
        assert score == 1.0  # Can't be more efficient than expected

    def test_empty_actual(self):
        """Test with empty actual trajectory."""
        outputs = {"trajectory": []}
        reference = {"trajectory": ["model", "search"]}

        score = trajectory_efficiency_score(outputs, reference)
        assert score == 0.0

    def test_no_expected(self):
        """Test with no expected trajectory (automatic pass)."""
        outputs = {"trajectory": ["model", "search"]}
        reference = {}

        score = trajectory_efficiency_score(outputs, reference)
        assert score == 1.0
