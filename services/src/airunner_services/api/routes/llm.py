"""LLM API routes backed by the runtime registry."""

from __future__ import annotations

from fastapi import APIRouter

from .llm_contracts import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    ModelInfo,
    ModelLoadRequest,
    RagIndexRequest,
)
from .llm_generation_routes import router as generation_router
from .llm_model_routes import router as model_router
from .llm_rag_routes import router as rag_router
from .llm_stream_routes import router as stream_router

router = APIRouter()
router.include_router(generation_router)
router.include_router(model_router)
router.include_router(rag_router)
router.include_router(stream_router)

__all__ = [
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatMessage",
    "CompletionRequest",
    "CompletionResponse",
    "ModelInfo",
    "ModelLoadRequest",
    "RagIndexRequest",
    "router",
]
