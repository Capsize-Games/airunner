"""Response model describing one daemon-visible runtime."""

from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel, Field


class RuntimeSummaryResponse(BaseModel):
    """Health and capability summary for one runtime client."""

    runtime: str
    provider: str
    mode: str
    transport: str
    status: str
    loaded: bool = False
    details: str = ""
    supports_streaming: bool = False
    allows_model_control: bool = False
    supports_cancellation: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    route_aliases: List[str] = Field(default_factory=list)
