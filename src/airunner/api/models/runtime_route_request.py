"""Request model for selecting a daemon runtime route."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class RuntimeRouteRequest(BaseModel):
    """Select a registered runtime route for daemon control."""

    provider: str = "local"
    deployment_mode: str = "default"
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)