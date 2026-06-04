"""Request/response models for text-to-speech endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TTSRequest(BaseModel):
    """TTS request."""

    text: str
    voice: Optional[str] = None
    speed: float = 1.0
    model: Optional[str] = None
    model_type: Optional[str] = None
    request_id: Optional[str] = None


class ModelInfo(BaseModel):
    """TTS model information."""

    id: str
    name: str
    loaded: bool
