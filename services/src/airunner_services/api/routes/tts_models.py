"""Request/response models for text-to-speech endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from airunner_services.runtimes.contracts import (
    TTS_NAME_MAX_LENGTH,
    TTS_SPEED_MAX,
    TTS_SPEED_MIN,
    TTS_TEXT_MAX_LENGTH,
)


class TTSRequest(BaseModel):
    """TTS request."""

    text: str
    voice: Optional[str] = None
    speed: float = 1.0
    model: Optional[str] = None
    model_type: Optional[str] = None
    request_id: Optional[str] = None


class TTSHTTPRequest(TTSRequest):
    """Bounded HTTP synthesis input; WebSocket rules stay wire-compatible."""

    model_config = ConfigDict(extra="ignore")

    text: str = Field(strict=True, max_length=TTS_TEXT_MAX_LENGTH)
    voice: Optional[str] = Field(
        default=None, strict=True, max_length=TTS_NAME_MAX_LENGTH
    )
    speed: float = Field(
        default=1.0,
        strict=True,
        allow_inf_nan=False,
        ge=TTS_SPEED_MIN,
        le=TTS_SPEED_MAX,
    )
    model: Optional[str] = Field(
        default=None, strict=True, max_length=TTS_NAME_MAX_LENGTH
    )
    model_type: Optional[str] = Field(
        default=None, strict=True, max_length=TTS_NAME_MAX_LENGTH
    )
    request_id: Optional[str] = Field(
        default=None, strict=True, max_length=TTS_NAME_MAX_LENGTH
    )

    @field_validator("text")
    @classmethod
    def _text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

    @field_validator("voice", "model", "model_type", "request_id")
    @classmethod
    def _identifiers_must_be_plain(
        cls, value: Optional[str]
    ) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("identifiers must not be blank")
        if any(char in normalized for char in ("\x00", "\n", "\r")):
            raise ValueError("identifiers contain invalid characters")
        return normalized


class ModelInfo(BaseModel):
    """TTS model information."""

    id: str
    name: str
    loaded: bool


class VoiceCatalogResponse(BaseModel):
    """Real voice identifiers exposed by a configured TTS catalog."""

    voices: list[StrictStr]

    @field_validator("voices")
    @classmethod
    def _voice_ids_must_be_plain(cls, values: list[str]) -> list[str]:
        for value in values:
            if not value.strip() or any(
                char in value for char in ("\x00", "\n", "\r")
            ):
                raise ValueError("voice catalog contains an invalid ID")
        return values
