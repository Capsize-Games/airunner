"""
Quality metrics for evaluating LLM responses in eval tests.

Provides utilities to measure:
- Response relevance and coherence
- Tool usage efficiency and correctness
- Factual accuracy
- Hallucination detection
- Instruction following

Usage:
    from airunner.components.eval.utils.quality_metrics import (
        evaluate_tool_usage,
        evaluate_response_quality,
        evaluate_conversation_coherence,
    )

    result = track_trajectory_sync(client, prompt)

    tool_metrics = evaluate_tool_usage(
        result,
        expected_tools=["create_agent"],
        max_calls=1,
    )
    assert tool_metrics["score"] > 0.8

    quality_metrics = evaluate_response_quality(
        result["response"],
        prompt,
    )
    assert quality_metrics["relevance"] > 0.7
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def evaluate_tool_usage(
    result: Dict[str, Any],
    expected_tools: Optional[List[str]] = None,
    max_calls: Optional[int] = None,
    min_calls: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Evaluate the quality of tool usage in an LLM response.

    Args:
        result: Result dict from track_trajectory_sync()
        expected_tools: List of tool names that should be called
        max_calls: Maximum number of tool calls (detect over-calling)
        min_calls: Minimum number of tool calls (detect under-calling)

    Returns:
        {
            "tool_called": bool,
            "correct_tools": bool,
            "correct_count": bool,
            "overcalling": bool,
            "undercalling": bool,
            "precision": float (0-1),
            "recall": float (0-1),
            "score": float (0-1),
            "details": str,
        }

    Example:
        >>> result = track_trajectory_sync(client, "Create an agent")
        >>> metrics = evaluate_tool_usage(
        ...     result,
        ...     expected_tools=["create_agent"],
        ...     max_calls=1,
        ... )
        >>> assert metrics["score"] > 0.8
    """
    tools_used = result.get("tools", [])
    tool_calls = result.get("tool_calls", [])
    num_calls = len(tool_calls)

    # Basic checks
    tool_called = len(tools_used) > 0
    correct_tools = True
    precision = 1.0
    recall = 1.0

    # Check if expected tools were called
    if expected_tools:
        called_tools = set(tools_used)
        expected_set = set(expected_tools)

        # Precision: What percentage of called tools were expected?
        if called_tools:
            precision = len(called_tools & expected_set) / len(called_tools)

        # Recall: What percentage of expected tools were called?
        if expected_set:
            recall = len(called_tools & expected_set) / len(expected_set)

        correct_tools = called_tools == expected_set

    # Check call count
    overcalling = max_calls is not None and num_calls > max_calls
    undercalling = min_calls is not None and num_calls < min_calls
    correct_count = not (overcalling or undercalling)

    # Calculate overall score (F1-like metric)
    if precision + recall > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0.0

    count_penalty = 0.2 if (overcalling or undercalling) else 0.0
    score = max(0.0, f1 - count_penalty)

    # Build details string
    details_parts = []
    if expected_tools:
        details_parts.append(
            f"Expected: {expected_tools}, Called: {tools_used}"
        )
    if overcalling:
        details_parts.append(
            f"Over-calling detected: {num_calls} > {max_calls}"
        )
    if undercalling:
        details_parts.append(
            f"Under-calling detected: {num_calls} < {min_calls}"
        )

    return {
        "tool_called": tool_called,
        "correct_tools": correct_tools,
        "correct_count": correct_count,
        "overcalling": overcalling,
        "undercalling": undercalling,
        "precision": precision,
        "recall": recall,
        "score": score,
        "details": " | ".join(details_parts) if details_parts else "OK",
    }


def evaluate_response_quality(
    response: str,
    prompt: str,
    expected_keywords: Optional[List[str]] = None,
    forbidden_keywords: Optional[List[str]] = None,
    min_length: int = 10,
    max_length: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Evaluate the quality of an LLM text response.

    Args:
        response: The LLM's text response
        prompt: The original prompt
        expected_keywords: Keywords that should appear (case-insensitive)
        forbidden_keywords: Keywords that should NOT appear (hallucination)
        min_length: Minimum acceptable response length
        max_length: Maximum acceptable response length

    Returns:
        {
            "relevance": float (0-1),
            "coherence": float (0-1),
            "completeness": float (0-1),
            "conciseness": float (0-1),
            "no_hallucination": bool,
            "score": float (0-1),
            "details": str,
        }

    Example:
        >>> response = "I've created a new agent named Helper."
        >>> metrics = evaluate_response_quality(
        ...     response,
        ...     "Create an agent named Helper",
        ...     expected_keywords=["created", "agent", "Helper"],
        ... )
        >>> assert metrics["relevance"] > 0.8
    """
    response_lower = response.lower()
    prompt.lower()

    # Relevance: Does response contain expected keywords?
    relevance = 1.0
    if expected_keywords:
        found = sum(
            1 for kw in expected_keywords if kw.lower() in response_lower
        )
        relevance = found / len(expected_keywords)

    # Hallucination check: Response shouldn't contain forbidden content
    no_hallucination = True
    hallucinated_words = []
    if forbidden_keywords:
        for kw in forbidden_keywords:
            if kw.lower() in response_lower:
                no_hallucination = False
                hallucinated_words.append(kw)

    # Completeness: Not empty or truncated
    completeness = 1.0 if len(response) >= min_length else 0.0

    # Conciseness: Within acceptable length
    conciseness = 1.0
    if max_length and len(response) > max_length:
        conciseness = max(0.0, 1.0 - (len(response) - max_length) / max_length)

    # Coherence: Basic checks (not just repeated chars, has spaces, etc.)
    coherence = 1.0
    if len(set(response)) < 5:  # Too few unique characters
        coherence = 0.5
    if response.count(" ") < len(response) / 50:  # No word breaks
        coherence = 0.5

    # Overall score
    weights = {
        "relevance": 0.35,
        "completeness": 0.25,
        "coherence": 0.20,
        "conciseness": 0.10,
        "no_hallucination": 0.10,
    }

    score = (
        weights["relevance"] * relevance
        + weights["completeness"] * completeness
        + weights["coherence"] * coherence
        + weights["conciseness"] * conciseness
        + weights["no_hallucination"] * (1.0 if no_hallucination else 0.0)
    )

    # Build details
    details_parts = []
    if expected_keywords and relevance < 1.0:
        missing = [
            kw for kw in expected_keywords if kw.lower() not in response_lower
        ]
        details_parts.append(f"Missing keywords: {missing}")
    if not no_hallucination:
        details_parts.append(f"Hallucinated: {hallucinated_words}")
    if completeness < 1.0:
        details_parts.append(f"Too short: {len(response)} < {min_length}")
    if conciseness < 1.0:
        details_parts.append(f"Too verbose: {len(response)} > {max_length}")

    return {
        "relevance": relevance,
        "coherence": coherence,
        "completeness": completeness,
        "conciseness": conciseness,
        "no_hallucination": no_hallucination,
        "score": score,
        "details": " | ".join(details_parts) if details_parts else "OK",
    }


def evaluate_conversation_coherence(
    conversation_history: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Evaluate coherence across multi-turn conversation.

    Args:
        conversation_history: List of {role, content} dicts

    Returns:
        {
            "turn_count": int,
            "context_maintained": bool,
            "no_repetition": bool,
            "score": float (0-1),
            "details": str,
        }

    Example:
        >>> conversation = [
        ...     {"role": "user", "content": "Create an agent"},
        ...     {"role": "assistant", "content": "Created Helper agent"},
        ...     {"role": "user", "content": "List my agents"},
        ...     {"role": "assistant", "content": "You have: Helper"},
        ... ]
        >>> metrics = evaluate_conversation_coherence(conversation)
        >>> assert metrics["context_maintained"]
    """
    turn_count = len([m for m in conversation_history if m["role"] == "user"])

    # Check for repetition (assistant saying same thing multiple times)
    assistant_messages = [
        m["content"] for m in conversation_history if m["role"] == "assistant"
    ]

    no_repetition = True
    if len(assistant_messages) > 1:
        # Check if any message is repeated
        for i, msg1 in enumerate(assistant_messages):
            for msg2 in assistant_messages[i + 1 :]:
                if msg1.lower().strip() == msg2.lower().strip():
                    no_repetition = False
                    break

    # Context maintenance: Later messages should reference earlier context
    context_maintained = True
    if turn_count > 1:
        # Simple heuristic: Check if assistant references earlier info
        # This is a basic check - could be more sophisticated
        for i in range(1, len(conversation_history)):
            if conversation_history[i]["role"] == "assistant":
                response = conversation_history[i]["content"].lower()
                # Check if response relates to previous user messages
                # For now, just verify it's not generic
                generic_phrases = [
                    "i don't know",
                    "i can't help",
                    "i don't understand",
                ]
                if any(phrase in response for phrase in generic_phrases):
                    context_maintained = False

    # Calculate score
    score = 1.0
    if not no_repetition:
        score -= 0.3
    if not context_maintained:
        score -= 0.4

    details_parts = []
    if not no_repetition:
        details_parts.append("Repetitive responses detected")
    if not context_maintained:
        details_parts.append("Context not maintained across turns")

    return {
        "turn_count": turn_count,
        "context_maintained": context_maintained,
        "no_repetition": no_repetition,
        "score": max(0.0, score),
        "details": " | ".join(details_parts) if details_parts else "OK",
    }


def assert_quality_threshold(
    metrics: Dict[str, Any],
    threshold: float = 0.7,
    metric_name: str = "quality",
) -> None:
    """
    Assert that quality metrics meet a threshold.

    Args:
        metrics: Metrics dict with "score" key
        threshold: Minimum acceptable score (0-1)
        metric_name: Name for error message

    Raises:
        AssertionError: If score below threshold

    Example:
        >>> metrics = evaluate_response_quality(response, prompt)
        >>> assert_quality_threshold(metrics, 0.8, "response quality")
    """
    score = metrics.get("score", 0.0)
    details = metrics.get("details", "")

    assert score >= threshold, (
        f"{metric_name} score {score:.2f} below threshold {threshold:.2f}\n"
        f"Details: {details}"
    )
