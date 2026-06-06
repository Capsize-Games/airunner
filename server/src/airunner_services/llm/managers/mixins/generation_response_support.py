"""Response extraction and fallback helpers for generation."""

from __future__ import annotations

import traceback
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage
from langgraph.errors import GraphRecursionError

from airunner_services.llm.gpt_oss_parser import (
    has_gpt_oss_markup,
    looks_like_tool_argument_payload,
    parse_gpt_oss_response,
)
from airunner_services.llm.managers.mixins.generation_signal_support import (
    _send_signal,
)

READ_ONLY_TASK_TOOLS = {
    "list_workspace_files",
    "read_code_file",
    "read_file",
    "search_files",
    "grep_search",
    "semantic_search",
    "get_document_content",
    "get_document_info",
    "search_document",
    "goto_document_line",
    "validate_code",
    "run_tests",
    "lint_code",
    "analyze_code_complexity",
    "execute_python",
}

MUTATING_TASK_TOOLS = {
    "create_code_file",
    "edit_code_file",
    "delete_code_file",
    "format_code_file",
    "format_code",
    "write_file",
    "edit_file",
    "delete_file",
    "edit_document_lines",
    "insert_document_lines",
    "delete_document_lines",
    "replace_in_document",
    "save_document",
}


def fallback_response_for_empty_result(
    result: Dict[str, Any],
    executed_tools: List[str],
) -> str:
    """Return a visible fallback when the model produced no final text."""
    messages = _result_messages(result)
    ai_messages = [
        message for message in messages or [] if isinstance(message, AIMessage)
    ]
    effective_tools = list(executed_tools)
    if not effective_tools:
        _extend_tools_from_messages(effective_tools, ai_messages)
    if effective_tools:
        return _tool_only_fallback(effective_tools)
    if any(getattr(message, "tool_calls", None) for message in ai_messages):
        return (
            "The model attempted a tool-based response but did not produce "
            "a final reply. No changes were applied."
        )
    if ai_messages:
        return (
            "The model produced an empty reply for this request. No changes "
            "were applied."
        )
    return ""


def _result_messages(result: Dict[str, Any]):
    """Return the raw or final messages from one result."""
    if not isinstance(result, dict):
        return []
    return result.get("raw_messages") or result.get("messages")


def _extend_tools_from_messages(
    effective_tools: list[str], ai_messages
) -> None:
    """Extend the executed tool list from AI message metadata."""
    for message in ai_messages:
        extra_tools = (message.additional_kwargs or {}).get("executed_tools")
        if isinstance(extra_tools, (list, tuple, set)):
            effective_tools.extend(
                str(tool_name) for tool_name in extra_tools if tool_name
            )


def _tool_only_fallback(effective_tools: list[str]) -> str:
    """Return the fallback message for tool-only completions."""
    tool_summary = ", ".join(dict.fromkeys(effective_tools))
    normalized_tools = set(effective_tools)
    if (
        not normalized_tools & MUTATING_TASK_TOOLS
        and normalized_tools <= READ_ONLY_TASK_TOOLS
    ):
        return (
            "The model inspected the workspace with read-only tools "
            f"({tool_summary}) but did not make any changes."
        )
    if not normalized_tools & MUTATING_TASK_TOOLS:
        return (
            f"The model used non-mutating tools ({tool_summary}) but did "
            "not make any changes."
        )
    return (
        "The request completed tool actions "
        f"({tool_summary}), but the model did not provide a final reply."
    )


def handle_interrupted_generation(
    owner,
    llm_request: Optional[Any],
    sequence_counter: int,
) -> str:
    """Handle interrupted generation and send an empty end marker."""
    owner.logger.info("Generation interrupted by user")
    _send_signal(
        owner,
        llm_request,
        "",
        is_end_of_message=True,
        sequence_number=sequence_counter + 1,
        message_type="assistant",
    )
    return ""


def _debug_print_error(exc: Exception, error_message: str) -> None:
    """Print error diagnostics to stdout for debugging."""
    print(f"[ERROR HANDLER] Exception type: {type(exc)}", flush=True)
    print(f"[ERROR HANDLER] Exception message: {str(exc)}", flush=True)
    print("[ERROR HANDLER] Full traceback:", flush=True)
    traceback.print_exc()
    print(
        f"[ERROR HANDLER] Error message to send: {error_message}",
        flush=True,
    )


def handle_generation_error(
    owner, exc: Exception, llm_request: Optional[Any]
) -> str:
    """Handle generation errors and emit the system error chunk."""
    owner.logger.error("Error during generation: %s", exc, exc_info=True)
    error_message = _generation_error_message(owner, exc)
    _debug_print_error(exc, error_message)
    _send_signal(
        owner,
        llm_request,
        error_message,
        is_end_of_message=False,
        message_type="system",
    )
    return error_message


def _generation_error_message(owner, exc: Exception) -> str:
    """Return the visible error message for one generation exception."""
    if not isinstance(exc, GraphRecursionError):
        return f"Error: {str(exc) if exc else 'Unknown error'}"
    executed_tools_value = getattr(
        owner._workflow_manager, "_executed_tools", []
    )
    executed_tools = []
    if isinstance(executed_tools_value, (list, tuple, set)):
        executed_tools = list(executed_tools_value)
    if any(tool in MUTATING_TASK_TOOLS for tool in executed_tools):
        return (
            "Error: The request hit the workflow recursion limit after "
            "applying some tool actions. Changes may already exist in the "
            "workspace, but the model did not finish verification."
        )
    return (
        "Error: The request got stuck repeating tool calls without making "
        "progress and hit the workflow recursion limit. No changes were "
        "applied."
    )


def _find_first_non_tool_message(
    final_messages: list[AIMessage],
) -> Optional[str]:
    """Return the first assistant message with visible content."""
    for message in reversed(final_messages):
        final_content = message.content or ""
        if not final_content or looks_like_tool_argument_payload(
            final_content
        ):
            continue
        if has_gpt_oss_markup(final_content):
            parsed = parse_gpt_oss_response(final_content)
            if parsed.content:
                return _normalize_final_content(parsed.content)
            continue
        if "\nAction:" in final_content:
            response_part = final_content.split("\nAction:")[0].strip()
            if response_part:
                return _normalize_final_content(response_part)
            continue
        return _normalize_final_content(final_content)
    return None


def extract_final_response(owner, result: Dict[str, Any]) -> str:
    """Extract the final visible assistant response from one result."""
    final_messages = _final_ai_messages(result)
    if not final_messages:
        owner.logger.info("No final AIMessage found in generation result")
        return ""
    content = _find_first_non_tool_message(final_messages)
    if content is not None:
        return content
    owner.logger.info("Final AIMessage was empty")
    return ""


def _final_ai_messages(result: Dict[str, Any]) -> list[AIMessage]:
    """Return the final AI messages from one generation result."""
    if not result or "messages" not in result:
        return []
    return [
        message
        for message in result["messages"]
        if isinstance(message, AIMessage)
    ]


def _normalize_final_content(content: str) -> str:
    """Strip one leading assistant label from a final model reply."""
    normalized = (content or "").lstrip()
    lowered = normalized.lower()
    for prefix in ("assistant\n", "assistant:"):
        if lowered.startswith(prefix):
            return normalized[len(prefix) :].lstrip()
    return normalized
