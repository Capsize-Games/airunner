"""Local-first routing matrix for companion pipelines (B12).

Every text-generation pipeline inventoried in W01 resolves here to the
*local* Desktop runtime registered under the default provider — the
same client ``/api/v1/llm/stream`` and ``/api/v1/llm/generate`` use.
An explicit online provider (OpenRouter) stays available only when the
caller passes both ``allow_remote`` and ``remote_consent``; denied or
missing local inference raises ``CompanionError`` and never silently
becomes a cloud call.

The embedding pipeline is local-only by construction: it resolves
through a ``CompanionEmbeddingClient`` identity (B04), never through
the LLM registry, so it has no registry route here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from airunner_services.runtimes.base import RuntimeClient
from airunner_services.runtimes.registry import (
    DEFAULT_PROVIDER,
    RuntimeRegistry,
    RuntimeRoute,
)
from airunner_services.runtimes.local_pipeline import (
    LOCAL_PIPELINE_ROUTES,
    REMOTE_PROVIDER_OPENROUTER,
    LocalInferencePipeline,
    LocalPipelineRoute,
)

from .contracts import (
    ERROR_INFERENCE_UNAVAILABLE,
    CompanionError,
    CompanionErrorCode,
)

# Compatibility aliases: companion policy keeps using its existing names,
# while the neutral runtime module owns the pipeline contract data.
CompanionPipeline = LocalInferencePipeline
PipelineRoute = LocalPipelineRoute
PIPELINE_ROUTES = LOCAL_PIPELINE_ROUTES


@dataclass(frozen=True)
class AdmissionVerdict:
    """Whether one inference call may proceed right now."""

    admitted: bool
    reason: str = ""


AdmissionCheck = Callable[[CompanionPipeline], AdmissionVerdict]


def allow_all_admission(pipeline: CompanionPipeline) -> AdmissionVerdict:
    """Admit every call (tests and single-tenant daemon default)."""
    del pipeline
    return AdmissionVerdict(admitted=True)


def deny_all_admission(reason: str) -> AdmissionCheck:
    """Build a check refusing every call (exhausted-resource tests)."""

    def _deny(pipeline: CompanionPipeline) -> AdmissionVerdict:
        del pipeline
        return AdmissionVerdict(admitted=False, reason=reason)

    return _deny


def check_admission(
    check: AdmissionCheck, pipeline: CompanionPipeline
) -> None:
    """Raise the retryable error when a call is not admitted."""
    verdict = check(pipeline)
    if not verdict.admitted:
        raise CompanionError(
            CompanionErrorCode(
                code=ERROR_INFERENCE_UNAVAILABLE,
                detail=f"'{pipeline.value}' not admitted: {verdict.reason}",
                retryable=True,
            )
        )


def _default_is_offline() -> bool:
    """Return the O01 offline-mode flag (lazy import)."""
    from airunner_services.url_safety import is_offline_mode

    return is_offline_mode()


def resolve_pipeline_client(
    registry: RuntimeRegistry,
    pipeline: CompanionPipeline,
    *,
    allow_remote: bool = False,
    remote_consent: bool = False,
    remote_provider: str = REMOTE_PROVIDER_OPENROUTER,
    is_offline: Optional[Callable[[], bool]] = None,
) -> RuntimeClient:
    """Resolve one pipeline to its runtime client (local by default)."""
    route = _llm_route_for(pipeline)
    if allow_remote and remote_consent:
        offline = (is_offline or _default_is_offline)()
        return _resolve_remote(registry, route, remote_provider, offline)
    try:
        return registry.resolve(route.runtime, DEFAULT_PROVIDER)
    except KeyError as exc:
        raise _retryable_unavailable(route, "retry when loaded") from exc


def _llm_route_for(pipeline: CompanionPipeline) -> PipelineRoute:
    """Return the registry route, rejecting non-LLM pipelines."""
    route = PIPELINE_ROUTES[pipeline]
    if route.runtime is None:
        raise CompanionError(
            CompanionErrorCode(
                code=ERROR_INFERENCE_UNAVAILABLE,
                detail=(
                    f"'{pipeline.value}' embeds through a local "
                    "CompanionEmbeddingClient, not the LLM registry"
                ),
            )
        )
    return route


def _resolve_remote(
    registry: RuntimeRegistry,
    route: PipelineRoute,
    remote_provider: str,
    offline: bool,
) -> RuntimeClient:
    """Resolve the explicit-consent remote route, or raise."""
    if offline:
        raise _remote_denied(route, "denied while offline")
    exact = RuntimeRoute(route.runtime, remote_provider)
    if not registry.has_route(exact):
        raise _remote_denied(
            route, f"provider '{remote_provider}' is not registered"
        )
    return registry.resolve(route.runtime, remote_provider)


def _retryable_unavailable(
    route: PipelineRoute, remedy: str
) -> CompanionError:
    """Build the retryable error for a missing local runtime."""
    assert route.runtime is not None
    return CompanionError(
        CompanionErrorCode(
            code=ERROR_INFERENCE_UNAVAILABLE,
            detail=(
                f"local {route.runtime.value} runtime unavailable "
                f"for '{route.pipeline.value}'; {remedy}"
            ),
            retryable=True,
        )
    )


def _remote_denied(route: PipelineRoute, why: str) -> CompanionError:
    """Build the non-retryable error for a denied remote route."""
    return CompanionError(
        CompanionErrorCode(
            code=ERROR_INFERENCE_UNAVAILABLE,
            detail=f"remote inference {why} for '{route.pipeline.value}'",
        )
    )


__all__ = [
    "AdmissionCheck",
    "AdmissionVerdict",
    "CompanionPipeline",
    "PIPELINE_ROUTES",
    "REMOTE_PROVIDER_OPENROUTER",
    "PipelineRoute",
    "allow_all_admission",
    "check_admission",
    "deny_all_admission",
    "resolve_pipeline_client",
]
