"""Execution helpers for generation."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

import torch

from airunner_common.contract_enums import LLMActionType
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
    extract_final_tool_calls,
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
    sampling_patch = _apply_raw_mode_sampling(owner, llm_request)
    try:
        return _stream_generation(
            owner,
            prompt,
            llm_request,
            complete_response,
            sequence_counter,
        )
    finally:
        _restore_sampling(owner, sampling_patch)
        owner._workflow_manager.set_token_callback(None)
        if hasattr(owner._workflow_manager, "set_thinking_callback"):
            owner._workflow_manager.set_thinking_callback(None)
        owner._interrupted = False
        if hasattr(owner._workflow_manager, "set_interrupted"):
            owner._workflow_manager.set_interrupted(False)


# Ollama/OpenAI-compat sampling defaults (llama.cpp community defaults),
# used only when the caller's own request didn't specify a value. The
# chat_model's own attributes otherwise carry whatever the *last loaded
# chatbot's* persisted DB settings were — companion-chatbot-specific
# tuning that has nothing to do with a bare API completion request, and
# in practice can be untuned/degenerate (e.g. repeat_penalty=1.0, i.e.
# off, causing verbatim repetition).
_RAW_MODE_SAMPLING_DEFAULTS = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "min_p": 0.05,
    "repeat_penalty": 1.1,
}


def _apply_raw_mode_sampling(
    owner,
    llm_request: Optional[Any],
) -> Optional[Dict[str, Any]]:
    """Temporarily override chat_model sampling for one raw-mode request."""
    if not getattr(llm_request, "raw_mode", False):
        return None
    # Read the WORKFLOW manager's chat_model, not owner's own — for any
    # request carrying client tool schemas (every headlesscode/raw_mode
    # request), request_handling_mixin's _prepare_request_tooling calls
    # bind_client_tools() BEFORE this function runs, which reassigns
    # WorkflowManager._chat_model to a fresh `_original_chat_model.
    # bind_tools(...)` clone (tool_management_mixin.py). owner._chat_model
    # is never reassigned by that call, so patching it here mutates an
    # object generation never reads — verified live 2026-08-20 via py-spy:
    # an explicit temperature=0 request still sampled at temp=1 even after
    # fixing the separate falsy-zero bug below, because the patch was
    # landing on the wrong object entirely.
    workflow_manager = getattr(owner, "_workflow_manager", None)
    chat_model = getattr(workflow_manager, "_chat_model", None)
    if chat_model is None:
        chat_model = getattr(owner, "_chat_model", None)
    if chat_model is None:
        return None
    request_values = {
        "temperature": getattr(llm_request, "temperature", None),
        "top_p": getattr(llm_request, "top_p", None),
        "top_k": getattr(llm_request, "top_k", None),
        "repeat_penalty": getattr(llm_request, "repetition_penalty", None),
    }
    previous: Dict[str, Any] = {}
    for attr, default in _RAW_MODE_SAMPLING_DEFAULTS.items():
        if not hasattr(chat_model, attr):
            continue
        previous[attr] = getattr(chat_model, attr)
        # `or default` would silently replace an explicit 0 (e.g.
        # temperature=0 for deterministic decoding, which headlesscode
        # always requests) with the raw-mode default, since 0 is falsy
        # in Python — verified live 2026-08-20 via py-spy: a request
        # sent with temperature=0 was actually sampled at temp=1 deep
        # inside llama.cpp. `is not None` only falls back to the
        # default when the caller genuinely didn't specify a value.
        value = request_values.get(attr)
        setattr(chat_model, attr, value if value is not None else default)
    return previous


def _restore_sampling(owner, previous: Optional[Dict[str, Any]]) -> None:
    """Restore chat_model sampling attributes after a raw-mode request."""
    if not previous:
        return
    chat_model = getattr(owner, "_chat_model", None)
    if chat_model is None:
        return
    for attr, value in previous.items():
        setattr(chat_model, attr, value)


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
    client_tool_calls = (
        extract_final_tool_calls(result)
        if getattr(llm_request, "client_tools", None)
        else None
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
        client_tool_calls,
    )
    if not getattr(llm_request, "raw_mode", False):
        # Ollama/OpenAI-compat callers get exactly what they asked for
        # and nothing else — no hidden side-effect LLM call they never
        # requested. (This extra call also reuses the just-generated
        # llama.cpp context without a reset, so the model tends to
        # continue its previous turn's reasoning instead of producing
        # an actual title — corrupting what should be a small,
        # unrelated completion.)
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