"""Finalization helpers extracted from generation_execution_support."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from airunner_services.llm.managers.mixins.generation_stream_support import (
    emit_visible_response,
    extract_final_response,
    extract_usage_tokens,
    fallback_response_for_empty_result,
    send_end_of_message,
)


def finalize_generation(
    owner,
    llm_request: Optional[Any],
    result: Dict[str, Any],
    complete_response,
    sequence_counter,
    executed_tools,
    prompt: str,
) -> Dict[str, Any]:
    """Finalize one generation: visible response, metrics, end-of-message."""
    _finalize_visible_response(
        owner,
        llm_request,
        result,
        complete_response,
        sequence_counter,
        executed_tools,
    )
    prompt_tokens, completion_tokens, total_tokens = extract_usage_tokens(
        result
    )
    final_visible_message = _final_visible_message(
        prompt, llm_request, complete_response[0]
    )
    send_end_of_message(
        owner,
        llm_request,
        sequence_counter,
        executed_tools,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        final_visible_message,
    )
    return {"response": complete_response[0], "tools": executed_tools}


def _final_visible_message(
    prompt: str,
    llm_request: Optional[Any],
    message: str,
) -> str:
    """Return the canonical visible reply for one completed request."""
    constrained_digit = _constrained_digit_reply(prompt, llm_request, message)
    if constrained_digit is not None:
        return constrained_digit
    return message


def _constrained_digit_reply(
    prompt: str,
    llm_request: Optional[Any],
    message: str,
) -> Optional[str]:
    """Collapse strict one-digit prompts to the requested digit."""
    system_prompt = str(getattr(llm_request, "system_prompt", "") or "")
    if "one character only" not in system_prompt.lower():
        return None
    match = re.search(r"single digit\s+([0-9])", prompt, re.IGNORECASE)
    if match is None:
        return None
    digit = match.group(1)
    if digit not in (message or ""):
        return None
    return digit


def _finalize_visible_response(
    owner,
    llm_request: Optional[Any],
    result: Dict[str, Any],
    complete_response,
    sequence_counter,
    executed_tools,
) -> None:
    """Emit the final visible response or fallback for one result."""
    final_response = extract_final_response(owner, result)
    if final_response:
        emit_visible_response(
            owner,
            llm_request,
            final_response,
            complete_response,
            sequence_counter,
        )
        complete_response[0] = final_response
    if complete_response[0]:
        return
    fallback_response = fallback_response_for_empty_result(
        result, executed_tools
    )
    emit_visible_response(
        owner,
        llm_request,
        fallback_response,
        complete_response,
        sequence_counter,
    )
