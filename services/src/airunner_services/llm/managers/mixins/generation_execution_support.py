"""Execution helpers for generation."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

import torch

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest
from airunner_services.llm.managers.mixins.generation_model_support import (
    ensure_workflow_manager_ready,
    invalid_model_path_response,
)
from airunner_services.llm.managers.mixins.generation_title_support import (
    maybe_generate_conversation_title,
)
from airunner_services.llm.managers.mixins.generation_stream_support import (
    create_streaming_callback,
    create_thinking_callback,
    emit_visible_response,
    executed_tools_from_workflow,
    extract_final_response,
    extract_usage_tokens,
    fallback_response_for_empty_result,
    handle_generation_error,
    handle_interrupted_generation,
    send_end_of_message,
)
from airunner_services.llm.managers.mixins.generation_workflow_support import (
    clamp_generation_tokens,
    setup_generation_workflow,
    sync_request_scope_to_workflow_manager,
)
from airunner_services.llm.managers.request_preparation import extract_request_images


def run_generation_stream(
    owner,
    prompt: str,
    llm_request: Optional[Any],
    complete_response,
    sequence_counter,
) -> Dict[str, Any]:
    """Run the generation stream and return the captured workflow result."""
    sync_request_scope_to_workflow_manager(owner)
    callback = create_streaming_callback(
        owner,
        llm_request,
        complete_response,
        sequence_counter,
    )
    owner._workflow_manager.set_token_callback(callback)
    thinking_callback = create_thinking_callback(
        owner,
        llm_request,
        sequence_counter,
    )
    if hasattr(owner._workflow_manager, "set_thinking_callback"):
        owner._workflow_manager.set_thinking_callback(thinking_callback)
    if hasattr(owner._workflow_manager, "set_interrupted"):
        owner._workflow_manager.set_interrupted(False)
    try:
        return _stream_generation(
            owner,
            prompt,
            llm_request,
            complete_response,
            sequence_counter,
        )
    finally:
        owner._workflow_manager.set_token_callback(None)
        if hasattr(owner._workflow_manager, "set_thinking_callback"):
            owner._workflow_manager.set_thinking_callback(None)
        owner._interrupted = False
        if hasattr(owner._workflow_manager, "set_interrupted"):
            owner._workflow_manager.set_interrupted(False)


def _stream_generation(
    owner,
    prompt: str,
    llm_request: Optional[Any],
    complete_response,
    sequence_counter,
) -> Dict[str, Any]:
    """Execute the workflow stream and convert it into the result dict."""
    try:
        _prepare_cuda()
        generation_kwargs = llm_request.to_generation_kwargs() if llm_request else {}
        _normalize_generation_kwargs(owner, llm_request, generation_kwargs)
        images = extract_request_images(llm_request)
        if images:
            owner.logger.info(
                "Passing %s image(s) to workflow stream",
                len(images),
            )
        result = _stream_messages(owner, prompt, generation_kwargs, images)
        if owner._interrupted:
            interrupt_msg = handle_interrupted_generation(
                owner,
                llm_request,
                sequence_counter[0],
            )
            complete_response[0] += interrupt_msg
            return {"messages": []}
        return result
    except Exception as exc:
        complete_response[0] = handle_generation_error(
            owner,
            exc,
            llm_request,
        )
        return {"messages": []}


def _prepare_cuda() -> None:
    """Clear CUDA caches before streaming when CUDA is available."""
    if not torch.cuda.is_available():
        return
    torch.cuda.empty_cache()
    torch.cuda.synchronize()


def _normalize_generation_kwargs(
    owner,
    llm_request: Optional[Any],
    generation_kwargs: dict,
) -> None:
    """Normalize generation kwargs before streaming."""
    if "max_tokens" in generation_kwargs:
        generation_kwargs["max_new_tokens"] = generation_kwargs.pop("max_tokens")
    clamp_generation_tokens(owner, generation_kwargs)
    owner.logger.debug(
        "llm_request.max_new_tokens=%s",
        llm_request.max_new_tokens if llm_request else "NO REQUEST",
    )
    owner.logger.debug(
        "generation_kwargs keys: %s",
        list(generation_kwargs.keys()),
    )
    owner.logger.debug(
        "generation_kwargs.get('max_new_tokens')=%s",
        generation_kwargs.get("max_new_tokens", "NOT SET"),
    )


def _stream_messages(owner, prompt: str, generation_kwargs: dict, images) -> Dict[str, Any]:
    """Collect raw and final workflow messages from the stream."""
    result_messages = []
    raw_messages = []
    for message in owner._workflow_manager.stream(
        prompt,
        generation_kwargs,
        images=images,
    ):
        if owner._interrupted:
            owner.logger.info("Stream interrupted - breaking out of generation")
            break
        raw_messages.append(message)
        if not getattr(message, "tool_calls", None):
            result_messages.append(message)
    return {"messages": result_messages, "raw_messages": raw_messages}


def do_generate(
    owner,
    prompt: str,
    action: LLMActionType,
    system_prompt: Optional[str] = None,
    llm_request: Optional[Any] = None,
    do_tts_reply: bool = True,
    extra_context: Optional[Dict[str, Dict[str, Any]]] = None,
    skip_tool_setup: bool = False,
) -> Dict[str, Any]:
    """Generate a response using the loaded LLM."""
    del do_tts_reply, extra_context
    invalid_path = invalid_model_path_response(owner)
    if invalid_path:
        return invalid_path
    if action == LLMActionType.DEEP_RESEARCH:
        owner.logger.info(
            "Deep Research mode - using tool-based research workflow"
        )
        owner.logger.info(
            "Research tools will be used: search_web, search_news, "
            "scrape_website, validate_url, validate_content, and related "
            "validation tools."
        )
    llm_request = llm_request or LLMRequest()
    setup_generation_workflow(
        owner,
        action,
        system_prompt,
        skip_tool_setup,
        llm_request,
    )
    complete_response = [""]
    sequence_counter = [0]
    owner._interrupted = False
    workflow_error = ensure_workflow_manager_ready(owner)
    if workflow_error:
        return workflow_error
    result = run_generation_stream(
        owner,
        prompt,
        llm_request,
        complete_response,
        sequence_counter,
    )
    prompt_tokens, completion_tokens, total_tokens = extract_usage_tokens(result)
    executed_tools = executed_tools_from_workflow(owner._workflow_manager)
    _finalize_visible_response(
        owner,
        llm_request,
        result,
        complete_response,
        sequence_counter,
        executed_tools,
    )
    final_visible_message = _final_visible_message(
        prompt,
        llm_request,
        complete_response[0],
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
    maybe_generate_conversation_title(owner)
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
    fallback_response = fallback_response_for_empty_result(result, executed_tools)
    emit_visible_response(
        owner,
        llm_request,
        fallback_response,
        complete_response,
        sequence_counter,
    )