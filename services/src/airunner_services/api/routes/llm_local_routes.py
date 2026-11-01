"""Route exposing the local-inference capability contract.

``GET /api/v1/llm/local-inference`` answers even when no LLM
runtime is registered or loaded: a Local Node consumer needs the
model/context/VRAM matrix and an honest ``unavailable`` health
marker, not a 503 it cannot distinguish from a dead daemon.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from airunner_services.llm.local_capability import (
    build_local_capability,
)

from .llm_runtime import get_runtime_registry

router = APIRouter()


class GgufInfo(BaseModel):
    """GGUF download identity for one local model."""

    supported: bool
    repo_id: Optional[str] = None
    filename: Optional[str] = None


class GgufProfile(BaseModel):
    """One named GGUF runtime profile."""

    name: str
    n_ctx: Optional[int] = None


class LocalModelCapability(BaseModel):
    """Capability entry for one supported local GGUF model."""

    id: str
    name: str
    configured: bool
    loaded: bool
    context_length: int
    function_calling: bool
    tool_calling_mode: str
    supports_thinking: bool
    vram_gb: Dict[str, int]
    gguf: GgufInfo
    gguf_runtime_profiles: List[GgufProfile] = Field(default_factory=list)


class PipelineCapability(BaseModel):
    """Local-first routing entry for one companion pipeline."""

    pipeline: str
    runtime: Optional[str] = None
    provider: str
    local_only: bool


class RuntimeDescriptorInfo(BaseModel):
    """Descriptor of the registered local LLM runtime."""

    runtime: str
    provider: str
    mode: str
    transport: str
    supports_streaming: bool
    allows_model_control: bool


class LocalRuntimeHealth(BaseModel):
    """Live health of the local LLM runtime, or unavailable."""

    status: str
    details: str = ""
    descriptor: Optional[RuntimeDescriptorInfo] = None


class RoutingInfo(BaseModel):
    """Default-local versus explicit-consent remote routing."""

    default_provider: str
    remote_provider: str
    remote_requires_consent: bool


class LocalInferenceCapability(BaseModel):
    """Full local-inference capability payload (contract v1)."""

    contract: str
    contract_version: str
    provider: str
    models: List[LocalModelCapability]
    pipelines: List[PipelineCapability]
    runtime: LocalRuntimeHealth
    routing: RoutingInfo
    endpoints: Dict[str, str]


def _configured_model_id() -> str:
    """Return the effective selection (never proof of a load).

    Falls back to the documented default local model when no
    selection is persisted; "" only when settings are unreadable.
    """
    try:
        from airunner_services.database.models.llm_generator_settings import (
            LLMGeneratorSettings,
        )

        from .llm_model_routes import selected_model_id

        return selected_model_id(LLMGeneratorSettings.objects.first())
    except Exception:
        return ""


@router.get("/local-inference", response_model=LocalInferenceCapability)
async def local_inference_capability(
    request: Request,
) -> LocalInferenceCapability:
    """Return supported local models, routing, and runtime health."""
    payload = build_local_capability(
        registry=get_runtime_registry(request),
        configured_model_id=_configured_model_id(),
    )
    return LocalInferenceCapability(**payload)


__all__ = ["LocalInferenceCapability", "router"]
