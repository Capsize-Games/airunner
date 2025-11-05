"""
Trajectory evaluation functions for agent testing.

This module provides evaluators for comparing expected and actual agent
trajectories, enabling measurement of path correctness and efficiency.
"""

from typing import Dict, List, Any


def trajectory_subsequence(
    outputs: Dict[str, Any], reference_outputs: Dict[str, Any]
) -> float:
    """
    Evaluate trajectory as subsequence match.

    Checks if the expected trajectory steps appear in order within the actual
    trajectory, allowing for extra steps in between. This is useful when you
    care about key steps being taken but don't want to require exact matching.

    Args:
        outputs: Agent outputs containing 'trajectory' key
        reference_outputs: Expected outputs containing 'trajectory' key

    Returns:
        Float between 0-1 representing percentage of expected steps found
        in correct order. Returns 1.0 if no expected trajectory specified.

    Example:
        >>> outputs = {'trajectory': ['model', 'tools', 'search', 'tools', 'model']}
        >>> reference = {'trajectory': ['model', 'search', 'model']}
        >>> trajectory_subsequence(outputs, reference)
        1.0  # All expected steps found in order

        >>> outputs = {'trajectory': ['model', 'model']}
        >>> reference = {'trajectory': ['model', 'search', 'model']}
        >>> trajectory_subsequence(outputs, reference)
        0.666...  # Only 2/3 steps found
    """
    expected = reference_outputs.get("trajectory", [])
    actual = outputs.get("trajectory", [])

    # No expected trajectory = automatic pass
    if not expected:
        return 1.0

    # Empty actual trajectory = fail
    if not actual:
        return 0.0

    # Check if expected is longer than actual = impossible to match
    if len(expected) > len(actual):
        # Still allow partial credit
        pass

    # Find subsequence match
    i = 0  # Index in expected
    j = 0  # Index in actual

    while i < len(expected) and j < len(actual):
        if expected[i] == actual[j]:
            i += 1  # Found match, advance expected
        j += 1  # Always advance actual

    # Score is percentage of expected steps found
    return i / len(expected) if expected else 1.0


def trajectory_exact_match(
    outputs: Dict[str, Any], reference_outputs: Dict[str, Any]
) -> bool:
    """
    Evaluate trajectory as exact match.

    Checks if the actual trajectory exactly matches the expected trajectory
    with no extra or missing steps.

    Args:
        outputs: Agent outputs containing 'trajectory' key
        reference_outputs: Expected outputs containing 'trajectory' key

    Returns:
        True if trajectories match exactly, False otherwise.
        Returns True if no expected trajectory specified.

    Example:
        >>> outputs = {'trajectory': ['model', 'tools', 'search', 'model']}
        >>> reference = {'trajectory': ['model', 'tools', 'search', 'model']}
        >>> trajectory_exact_match(outputs, reference)
        True

        >>> outputs = {'trajectory': ['model', 'search', 'model']}
        >>> reference = {'trajectory': ['model', 'tools', 'search', 'model']}
        >>> trajectory_exact_match(outputs, reference)
        False
    """
    expected = reference_outputs.get("trajectory", [])
    actual = outputs.get("trajectory", [])

    # No expected trajectory = automatic pass
    if not expected:
        return True

    # Exact match
    return expected == actual


def trajectory_contains(
    outputs: Dict[str, Any], required_steps: List[str]
) -> bool:
    """
    Check if trajectory contains all required steps (order doesn't matter).

    Useful for checking if specific tools were used without caring about
    the exact sequence or any extra steps.

    Args:
        outputs: Agent outputs containing 'trajectory' key
        required_steps: List of steps that must appear in trajectory

    Returns:
        True if all required steps are present, False otherwise.

    Example:
        >>> outputs = {'trajectory': ['model', 'tools', 'search', 'rag', 'model']}
        >>> trajectory_contains(outputs, ['search', 'rag'])
        True

        >>> trajectory_contains(outputs, ['search', 'code'])
        False
    """
    actual = outputs.get("trajectory", [])

    # Check if all required steps are in actual trajectory
    return all(step in actual for step in required_steps)


def trajectory_tool_usage(outputs: Dict[str, Any]) -> Dict[str, int]:
    """
    Count tool usage frequency in trajectory.

    Useful for detecting redundant tool calls or analyzing tool usage patterns.

    Args:
        outputs: Agent outputs containing 'trajectory' or 'tools' key

    Returns:
        Dictionary mapping tool names to call counts

    Example:
        >>> outputs = {
        ...     'trajectory': ['model', 'search', 'search', 'rag', 'model']
        ... }
        >>> trajectory_tool_usage(outputs)
        {'search': 2, 'rag': 1}
    """
    # Try to get tools list first, fall back to trajectory
    tools = outputs.get("tools", [])
    if not tools:
        # Extract tools from trajectory (skip 'model' and other node names)
        trajectory = outputs.get("trajectory", [])
        # Heuristic: tools are lowercase and don't contain 'model' or 'force'
        tools = [
            step
            for step in trajectory
            if step not in ["model", "force_response", "tools"]
        ]

    # Count occurrences
    tool_counts = {}
    for tool in tools:
        tool_counts[tool] = tool_counts.get(tool, 0) + 1

    return tool_counts


def trajectory_efficiency_score(
    outputs: Dict[str, Any], reference_outputs: Dict[str, Any]
) -> float:
    """
    Calculate efficiency score based on trajectory length.

    Compares actual trajectory length to expected length. Penalizes
    longer paths (redundant steps) and rewards shorter paths.

    Args:
        outputs: Agent outputs containing 'trajectory' key
        reference_outputs: Expected outputs containing 'trajectory' key

    Returns:
        Float between 0-1 where 1.0 is most efficient.
        Returns 1.0 if no expected trajectory specified.

    Example:
        >>> outputs = {'trajectory': ['model', 'search', 'model']}
        >>> reference = {'trajectory': ['model', 'search', 'model']}
        >>> trajectory_efficiency_score(outputs, reference)
        1.0  # Same length = perfect efficiency

        >>> outputs = {'trajectory': ['model', 'search', 'search', 'model']}
        >>> reference = {'trajectory': ['model', 'search', 'model']}
        >>> trajectory_efficiency_score(outputs, reference)
        0.75  # 25% longer = 75% efficient
    """
    expected = reference_outputs.get("trajectory", [])
    actual = outputs.get("trajectory", [])

    # No expected trajectory = automatic pass
    if not expected:
        return 1.0

    # Empty actual = fail
    if not actual:
        return 0.0

    # Calculate efficiency as expected_length / actual_length
    # Capped at 1.0 (can't be more efficient than expected)
    efficiency = min(1.0, len(expected) / len(actual))

    return efficiency
