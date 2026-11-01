"""Generic local-inference pipeline names and routing descriptors.

This module contains only the machine-readable pipeline/runtime mapping.
Application-specific admission, consent, and error policy belongs to the
consumer that resolves these routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from airunner_services.runtimes.contracts import RuntimeKind
from airunner_services.runtimes.registry import DEFAULT_PROVIDER


REMOTE_PROVIDER_OPENROUTER = "openrouter"


class LocalInferencePipeline(str, Enum):
    """Names of inference pipelines exposed by the local service."""

    DIALOGUE = "dialogue"
    FACT_EXTRACTION = "fact_extraction"
    MOOD_UPDATE = "mood_update"
    ROLLING_COMPRESSION = "rolling_compression"
    EPISODIC_SUMMARY = "episodic_summary"
    MEMORY_BLEND = "memory_blend"
    CURIOSITY = "curiosity"
    EMBEDDING = "embedding"


@dataclass(frozen=True)
class LocalPipelineRoute:
    """Runtime descriptor for one named inference pipeline."""

    pipeline: LocalInferencePipeline
    runtime: Optional[RuntimeKind]
    provider: str = DEFAULT_PROVIDER


def _llm_route(pipeline: LocalInferencePipeline) -> LocalPipelineRoute:
    return LocalPipelineRoute(pipeline=pipeline, runtime=RuntimeKind.LLM)


LOCAL_PIPELINE_ROUTES: Dict[LocalInferencePipeline, LocalPipelineRoute] = {
    pipeline: _llm_route(pipeline)
    for pipeline in (
        LocalInferencePipeline.DIALOGUE,
        LocalInferencePipeline.FACT_EXTRACTION,
        LocalInferencePipeline.MOOD_UPDATE,
        LocalInferencePipeline.ROLLING_COMPRESSION,
        LocalInferencePipeline.EPISODIC_SUMMARY,
        LocalInferencePipeline.MEMORY_BLEND,
        LocalInferencePipeline.CURIOSITY,
    )
}
LOCAL_PIPELINE_ROUTES[LocalInferencePipeline.EMBEDDING] = LocalPipelineRoute(
    pipeline=LocalInferencePipeline.EMBEDDING,
    runtime=None,
)


__all__ = [
    "LOCAL_PIPELINE_ROUTES",
    "REMOTE_PROVIDER_OPENROUTER",
    "LocalInferencePipeline",
    "LocalPipelineRoute",
]
