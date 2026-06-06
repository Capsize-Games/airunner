"""Response model for combined daemon lifecycle and runtime status."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from airunner_services.api.models.runtime_summary_response import (
    RuntimeSummaryResponse,
)
from airunner_services.api.routes.health import DaemonStatusResponse


class DaemonRuntimeStatusResponse(BaseModel):
    """Combined daemon lifecycle and runtime summary payload."""

    lifecycle: DaemonStatusResponse
    runtimes: List[RuntimeSummaryResponse] = Field(default_factory=list)
