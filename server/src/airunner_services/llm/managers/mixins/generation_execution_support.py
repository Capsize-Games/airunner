"""Execution helpers for generation."""

from __future__ import annotations

from typing import Any, Dict, Optional

import torch

from airunner_services.contract_enums import LLMActionType
from airunner_services.llm.llm_request import LLMRequest
from airunner_services.llm.managers.mixins.generation_execution_finalize import (
    finalize_generation,
)
from airunner_services.llm.managers.mixins.generation_model_support import (
    ensure_workflow_manager_ready,
    invalid_model_path_response,
)
from airunner_services.llm.managers.mixins.generation_stream_support import (
    create_streaming_callback,
    create_thinking_callback,
    executed_tools_from_workflow,
    handle_generation_error,
    handle_interrupted_generation,
)
from airunner_services.llm.managers.mixins.generation_workflow_support import (
    clamp_generation_tokens,
    setup_generation_workflow,
    sync_request_scope_to_workflow_manager,
)
from airunner_services.llm.managers.request_preparation import (
    extract_request_images,
)


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
        owner, llm_request, complete_response, sequence_counter
    )
    owner._workflow_manager.set_token_callback(callback)
    thinking_callback = create_thinking_callback(
        owner, llm_request, sequence_counter
    )
    if hasattr(owner._workflow_manager, "set_thinking_callback"):
        owner._workflow_manager.set_thinking_callback(thinking_callback)
    if hasattr(owner._workflow_manager, "set_interrupted"):
        owner._workflow_manager.set_interrupted(False)
    try:
        return _stream_generation(
            owner, prompt, llm_request, complete_response, sequence_counter
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
        generation_kwargs = (
            llm_request.to_generation_kwargs() if llm_request else {}
        )
        _normalize_generation_kwargs(owner, llm_request, generation_kwargs)
        images = extract_request_images(llm_request)
        if images:
            owner.logger.info(
                "Passing %s image(s) to workflow stream", len(images)
            )
        result = _stream_messages(owner, prompt, generation_kwargs, images)
        if owner._interrupted:
            interrupt_msg = handle_interrupted_generation(
                owner, llm_request, sequence_counter[0]
            )
            complete_response[0] += interrupt_msg
            return {"messages": []}
        return result
    except Exception as exc:
        complete_response[0] = handle_generation_error(owner, exc, llm_request)
        return {"messages": []}


def _prepare_cuda() -> None:
    """Clear CUDA caches before streaming when CUDA is available."""
    if not torch.cuda.is_available():
        return
    torch.cuda.empty_cache()
    torch.cuda.synchronize()


def _normalize_generation_kwargs(
    owner, llm_request, generation_kwargs: dict
) -> None:
    """Normalize generation kwargs before streaming."""
    if "max_tokens" in generation_kwargs:
        generation_kwargs["max_new_tokens"] = generation_kwargs.pop(
            "max_tokens"
        )
    clamp_generation_tokens(owner, generation_kwargs)
    owner.logger.debug(
        "llm_request.max_new_tokens=%s",
        llm_request.max_new_tokens if llm_request else "NO REQUEST",
    )
    owner.logger.debug(
        "generation_kwargs keys: %s", list(generation_kwargs.keys())
    )
    owner.logger.debug(
        "generation_kwargs.get('max_new_tokens')=%s",
        generation_kwargs.get("max_new_tokens", "NOT SET"),
    )


def _stream_messages(
    owner, prompt: str, generation_kwargs: dict, images
) -> Dict[str, Any]:
    """Collect raw and final workflow messages from the stream."""
    result_messages = []
    raw_messages = []
    for message in owner._workflow_manager.stream(
        prompt, generation_kwargs, images=images
    ):
        if owner._interrupted:
            owner.logger.info(
                "Stream interrupted - breaking out of generation"
            )
            break
        raw_messages.append(message)
        if not getattr(message, "tool_calls", None):
            result_messages.append(message)
    return {"messages": result_messages, "raw_messages": raw_messages}


def _log_deep_research_action(owner, action: LLMActionType) -> None:
    """Log diagnostics for deep research mode."""
    if action == LLMActionType.DEEP_RESEARCH:
        owner.logger.info(
            "Deep Research mode - using tool-based research workflow"
        )
        owner.logger.info(
            "Research tools will be used: search_web, search_news, "
            "scrape_website, validate_url, validate_content, and validation tools."
        )


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
    _log_deep_research_action(owner, action)
    llm_request = llm_request or LLMRequest()
    setup_generation_workflow(
        owner, action, system_prompt, skip_tool_setup, llm_request
    )
    complete_response = [""]
    sequence_counter = [0]
    owner._interrupted = False
    workflow_error = ensure_workflow_manager_ready(owner)
    if workflow_error:
        return workflow_error
    result = run_generation_stream(
        owner, prompt, llm_request, complete_response, sequence_counter
    )
    executed_tools = executed_tools_from_workflow(owner._workflow_manager)
    return finalize_generation(
        owner,
        llm_request,
        result,
        complete_response,
        sequence_counter,
        executed_tools,
        prompt,
    )
