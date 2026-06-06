"""Contracts for runtime-backed LLM routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Chat message submitted to the HTTP API."""

    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """Chat completion request."""

    messages: List[ChatMessage]
    model: Optional[str] = None
    gguf_runtime_profile: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    llm_overrides: Optional[Dict[str, Dict[str, Any]]] = None
    active_document_ids: Optional[List[int]] = None


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""

    content: str
    model: str
    finish_reason: str


class CompletionRequest(BaseModel):
    """Text completion request."""

    prompt: str
    gguf_runtime_profile: Optional[str] = None
    max_tokens: int = 100
    temperature: float = 0.7


class CompletionResponse(BaseModel):
    """Text completion response."""

    text: str
    finish_reason: str


class ModelInfo(BaseModel):
    """LLM model information."""

    id: str
    name: str
    loaded: bool
    size_mb: Optional[int] = None


class ModelLoadRequest(BaseModel):
    """Model load request."""

    model_id: str


class RagIndexRequest(BaseModel):
    """Document indexing request."""

    file_paths: Optional[List[str]] = None


__all__ = [
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatMessage",
    "CompletionRequest",
    "CompletionResponse",
    "ModelInfo",
    "ModelLoadRequest",
    "RagIndexRequest",
]
