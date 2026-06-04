"""
Trajectory tracking utilities for agent evaluation.

This module provides tools for tracking the execution path of agents through
nodes and tool calls, enabling trajectory-based evaluation.
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


async def track_trajectory(
    client: Any,
    prompt: str,
    max_tokens: int = 500,
    tool_categories: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Execute agent and track trajectory through nodes and tools.

    This function runs the agent with the given prompt and captures the
    sequence of nodes visited and tools called during execution.

    Args:
        client: AI runner client instance (from fixture)
        prompt: User prompt to process
        max_tokens: Maximum tokens for response
        tool_categories: Optional list of tool categories to enable
        **kwargs: Additional arguments passed to client.generate()

    Returns:
        Dictionary containing:
            - response: Final response text
            - trajectory: List of node/tool names in order visited
            - tool_calls: List of tool call details with args
            - nodes: List of node names visited
            - tools: List of tool names called

    Example:
        >>> result = await track_trajectory(
        ...     client,
        ...     "Remember my email is joe@example.com",
        ...     tool_categories=["USER_DATA"]
        ... )
        >>> result['trajectory']
        ['model', 'tools', 'store_user_data', 'model']
        >>> result['response']
        "I've stored your email address."
    """
    trajectory = []
    tool_calls = []
    nodes = []
    tools = []
    response_text = ""

    # Check if client has streaming support
    if hasattr(client, "astream_events"):
        # Use streaming API to capture events
        try:
            async for event in client.astream_events(
                prompt=prompt,
                max_tokens=max_tokens,
                tool_categories=tool_categories,
                **kwargs,
            ):
                event_type = event.get("type")
                payload = event.get("payload", {})

                if event_type == "node":
                    # Node transition
                    node_name = payload.get("name", "unknown")
                    trajectory.append(node_name)
                    nodes.append(node_name)
                    logger.debug(f"Node: {node_name}")

                elif event_type == "tool":
                    # Tool call
                    tool_name = payload.get("tool_name", "unknown")
                    tool_args = payload.get("args", {})
                    trajectory.append(tool_name)
                    tools.append(tool_name)
                    tool_calls.append(
                        {
                            "tool": tool_name,
                            "args": tool_args,
                        }
                    )
                    logger.debug(f"Tool: {tool_name}")

                elif event_type == "response":
                    # Final response
                    response_text = payload.get("text", "")
                    logger.debug(f"Response: {response_text[:100]}...")

        except AttributeError:
            logger.warning(
                "Client streaming not fully implemented, falling back to generate()"
            )
            # Fallback to regular generate
            response = client.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                tool_categories=tool_categories,
                **kwargs,
            )
            response_text = response.get("text", "")

            # Try to infer trajectory from response metadata if available
            if "trajectory" in response:
                trajectory = response["trajectory"]
            if "tool_calls" in response:
                tool_calls = response["tool_calls"]

    else:
        # Client doesn't have streaming, use regular generate
        logger.warning(
            "Client does not support astream_events, using generate() without trajectory"
        )
        response = client.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            tool_categories=tool_categories,
            **kwargs,
        )
        response_text = response.get("text", "")

        # Try to extract trajectory from response if available
        if "trajectory" in response:
            trajectory = response["trajectory"]
        if "tool_calls" in response:
            tool_calls = response["tool_calls"]
        if "nodes" in response:
            nodes = response["nodes"]
        if "tools" in response:
            tools = response["tools"]

    return {
        "response": response_text,
        "trajectory": trajectory,
        "tool_calls": tool_calls,
        "nodes": nodes,
        "tools": tools,
    }


def track_trajectory_sync(
    client: Any,
    prompt: str,
    max_tokens: int = 500,
    tool_categories: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Synchronous version of track_trajectory for non-async tests.

    Args:
        client: AI runner client instance
        prompt: User prompt to process
        max_tokens: Maximum tokens for response
        tool_categories: Optional list of tool categories to enable
        **kwargs: Additional arguments passed to client.generate()

    Returns:
        Same as track_trajectory()

    Example:
        >>> result = track_trajectory_sync(
        ...     client,
        ...     "What's my email?",
        ...     tool_categories=["USER_DATA"]
        ... )
    """
    # For now, just use generate() since we don't have sync streaming
    response = client.generate(
        prompt=prompt,
        max_tokens=max_tokens,
        tool_categories=tool_categories,
        **kwargs,
    )

    print(f"[TRACKING] Response keys: {list(response.keys())}", flush=True)
    print(
        f"[TRACKING] Response tools: {response.get('tools', 'KEY_NOT_FOUND')}",
        flush=True,
    )

    response_text = response.get("text", "")
    trajectory = response.get("trajectory", [])
    tool_calls = response.get("tool_calls", [])
    nodes = response.get("nodes", [])
    tools = response.get("tools", [])

    return {
        "response": response_text,
        "trajectory": trajectory,
        "tool_calls": tool_calls,
        "nodes": nodes,
        "tools": tools,
    }
