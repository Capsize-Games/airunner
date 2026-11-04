"""HTTP generation routes for runtime-backed LLM endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from airunner_services.runtimes.contracts import ChatMessage as RuntimeChatMessage
from airunner_services.runtimes.contracts import MessageRole

from .llm_contracts import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    CompletionRequest,
    CompletionResponse,
)
from .llm_runtime import (
    invoke_llm_runtime,
    require_runtime_registry,
    require_sidecar_for_function_tools,
    resolve_llm_client,
    to_runtime_messages,
)

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatCompletionResponse,
    response_model_exclude_none=True,
)
async def chat_completion(request: ChatCompletionRequest, req: Request):
    """Run chat completion against the runtime-backed local LLM."""
    if request.stream:
        raise HTTPException(
            status_code=400,
            detail=(
                "Streaming is not supported by /api/v1/llm/chat; "
                "use the /api/v1/llm/stream WebSocket endpoint."
            ),
        )
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    client = resolve_llm_client(require_runtime_registry(req))
    runtime_messages = to_runtime_messages(request.messages)
    require_sidecar_for_function_tools(
        client, runtime_messages, request.tools, request.tool_choice
    )
    content, finish_reason, tool_calls, usage = await invoke_llm_runtime(
        client,
        runtime_messages,
        request.model,
        request.gguf_runtime_profile,
        request.temperature,
        request.max_tokens,
        request.enable_thinking,
        request.tools,
        request.tool_choice,
    )
    return ChatCompletionResponse(
        content=content,
        model=request.model or "default",
        finish_reason=finish_reason,
        tool_calls=tool_calls or None,
        usage=usage or None,
    )


@router.post("/completion", response_model=CompletionResponse)
async def text_completion(request: CompletionRequest, req: Request):
    """Run text completion against the runtime-backed local LLM."""
    client = resolve_llm_client(require_runtime_registry(req))
    text, finish_reason, _tool_calls, _usage = await invoke_llm_runtime(
        client,
        [RuntimeChatMessage(role=MessageRole.USER, content=request.prompt)],
        None,
        request.gguf_runtime_profile,
        request.temperature,
        request.max_tokens,
        request.enable_thinking,
    )
    return CompletionResponse(text=text, finish_reason=finish_reason)
