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
    resolve_llm_client,
    to_runtime_messages,
)

router = APIRouter()


@router.post("/chat", response_model=ChatCompletionResponse)
async def chat_completion(request: ChatCompletionRequest, req: Request):
    """Run chat completion against the runtime-backed local LLM."""
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    client = resolve_llm_client(require_runtime_registry(req))
    response = await invoke_llm_runtime(
        client,
        to_runtime_messages(request.messages),
        request.model,
        request.gguf_runtime_profile,
        request.temperature,
        request.max_tokens,
    )
    return ChatCompletionResponse(
        content=response,
        model=request.model or "default",
        finish_reason="stop",
    )


@router.post("/completion", response_model=CompletionResponse)
async def text_completion(request: CompletionRequest, req: Request):
    """Run text completion against the runtime-backed local LLM."""
    client = resolve_llm_client(require_runtime_registry(req))
    response = await invoke_llm_runtime(
        client,
        [RuntimeChatMessage(role=MessageRole.USER, content=request.prompt)],
        None,
        request.gguf_runtime_profile,
        request.temperature,
        request.max_tokens,
    )
    return CompletionResponse(text=response, finish_reason="stop")