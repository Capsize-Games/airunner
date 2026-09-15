"""Request/response models for speech-to-text endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TranscriptionResponse(BaseModel):
    """Transcription response."""

    text: str
    language: Optional[str] = None


class ModelInfo(BaseModel):
    """STT model information."""

    id: str
    name: str
    loaded: bool
