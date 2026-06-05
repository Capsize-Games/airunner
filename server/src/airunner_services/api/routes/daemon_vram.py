"""VRAM coordination helpers for daemon route endpoints."""

from __future__ import annotations

import logging
import time

from fastapi import HTTPException, Request

from airunner_services.api.models.runtime_route_request import (
    RuntimeRouteRequest,
)
from airunner_services.runtimes.contracts import RuntimeAction, RuntimeKind

from .daemon_runtime_actions import (
    invoke_runtime_action,
    resolve_runtime_client,
)
from .daemon_runtime_registry import parse_runtime_kind
from .daemon_runtime_summary import (
    collect_runtime_summaries,
    summary_matches_route,
)

VRAM_UNLOAD_TIMEOUT_SECONDS = 15.0
VRAM_UNLOAD_POLL_SECONDS = 0.1


def wait_for_runtime_unload(
    request: Request,
    runtime: RuntimeKind,
    provider: str,
    deployment_mode: str,
) -> None:
    """Block until one runtime summary reports the route as unloaded."""
    deadline = time.monotonic() + VRAM_UNLOAD_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        summaries = collect_runtime_summaries(request)
        matching_summary = next(
            (
                summary
                for summary in summaries
                if summary_matches_route(
                    summary,
                    runtime,
                    provider,
                    deployment_mode,
                )
            ),
            None,
        )
        if matching_summary is None or not matching_summary.loaded:
            return
        time.sleep(VRAM_UNLOAD_POLL_SECONDS)
    raise HTTPException(
        status_code=504,
        detail=(
            f"Timed out waiting for {runtime.value} "
            f"({provider}:{deployment_mode}) to unload"
        ),
    )


def ensure_vram_available_for(
    request: Request,
    route_request: RuntimeRouteRequest,
    target_runtime: RuntimeKind,
) -> None:
    """Unload conflicting loaded runtimes before one target load/invoke."""
    logger = logging.getLogger(__name__)
    summaries = collect_runtime_summaries(request)
    logger.info(
        "VRAM check for %s: found %d runtime summaries",
        target_runtime.value,
        len(summaries),
    )
    for summary in summaries:
        logger.info(
            "  runtime=%s loaded=%s provider=%s mode=%s",
            summary.runtime,
            summary.loaded,
            summary.provider,
            summary.mode,
        )
    for summary in summaries:
        if not summary.loaded or summary.runtime == target_runtime.value:
            continue
        other_runtime = parse_runtime_kind(summary.runtime)
        if {target_runtime, other_runtime} == {
            RuntimeKind.LLM,
            RuntimeKind.TTS,
        }:
            continue
        logger.info(
            "Unloading %s (%s:%s) to free VRAM for %s",
            other_runtime.value,
            summary.provider,
            summary.mode,
            target_runtime.value,
        )
        other_client = resolve_runtime_client(
            request,
            other_runtime,
            summary.provider,
            summary.mode,
        )
        unload_request = RuntimeRouteRequest(
            provider=summary.provider,
            deployment_mode=summary.mode,
            request_id=route_request.request_id,
            metadata=dict(route_request.metadata or {}),
        )
        if (
            target_runtime is RuntimeKind.LLM
            and other_runtime is RuntimeKind.ART
        ):
            if summary.mode == "sidecar":
                unload_request.metadata["release_process"] = True
        invoke_runtime_action(
            other_client,
            other_runtime,
            RuntimeAction.UNLOAD_MODEL,
            unload_request,
        )
        wait_for_runtime_unload(
            request,
            other_runtime,
            summary.provider,
            summary.mode,
        )
