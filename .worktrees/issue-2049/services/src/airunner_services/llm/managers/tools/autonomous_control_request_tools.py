"""Builders for autonomous-control user request tools."""

from __future__ import annotations

import json
from typing import Callable, Optional

from langchain_core.tools import tool

from airunner_services.tools.base_tool import BaseTool


def _tool_error(owner: BaseTool, action: str, exc: Exception) -> str:
    """Log and format one request-tool error."""
    owner.logger.error("Error %s: %s", action, exc)
    return f"Error {action}: {exc}"


def _request_user_input_data(
    prompt: str,
    input_type: str,
    options: Optional[str],
    timeout_seconds: int,
) -> dict:
    """Build one request-user-input payload."""
    request_data = {
        "prompt": prompt,
        "input_type": input_type,
        "timeout_seconds": timeout_seconds,
    }
    if options:
        request_data["options"] = json.loads(options)
    return request_data


def _request_user_input_result(
    owner: BaseTool,
    prompt: str,
    input_type: str,
    options: Optional[str],
    timeout_seconds: int,
) -> str:
    """Request user input through the configured action handler."""
    try:
        request_data = _request_user_input_data(
            prompt,
            input_type,
            options,
            timeout_seconds,
        )
    except json.JSONDecodeError:
        return f"Error: options must be valid JSON list. Got: {options}"
    if not owner.dispatch_tool_action("request_user_input", request_data):
        return "User input requests are unavailable in this runtime."
    return f"Requested user input: '{prompt}' (waiting for response...)"


def build_request_user_input_tool(owner: BaseTool) -> Callable:
    """Build the user-input request tool."""

    @tool
    def request_user_input(
        prompt: str,
        input_type: str = "text",
        options: Optional[str] = None,
        timeout_seconds: int = 300,
    ) -> str:
        """Request input or approval from the user."""
        try:
            return _request_user_input_result(
                owner,
                prompt,
                input_type,
                options,
                timeout_seconds,
            )
        except Exception as exc:
            return _tool_error(owner, "requesting user input", exc)

    return request_user_input