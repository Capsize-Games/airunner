"""
Evaluation utilities for testing and validating AI agents.

This package provides tools for trajectory tracking, evaluation metrics,
and test helpers for comprehensive agent testing.
"""

from airunner.components.eval.utils.tracking import track_trajectory
from airunner.components.eval.utils.trajectory_evaluator import (
    trajectory_subsequence,
    trajectory_exact_match,
    trajectory_contains,
)

__all__ = [
    "track_trajectory",
    "trajectory_subsequence",
    "trajectory_exact_match",
    "trajectory_contains",
]
