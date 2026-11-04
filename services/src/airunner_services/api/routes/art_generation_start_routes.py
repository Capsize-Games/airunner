"""Generation-start routes for art API endpoints."""

import asyncio
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from airunner_common.settings import AIRUNNER_LOG_LEVEL
from airunner_services.art.utils.nsfw_checker import check_images_mandatory
from airunner_services.content_safety import ContentSafetyResult
from airunner_services.content_safety_gate import (
    evaluate_prompt_fields,
    rejection_message,
)
from airunner_services.utils.application import get_logger
from airunner_services.utils.job_tracker import (
    JobTracker,
)

from .art_contracts import (
    GenerationRequest,
    GenerationResponse,
    decode_input_image,
)
from .art_generation_model import resolve_generation_model
from .art_job_runner import build_generation_job_metadata, run_art_job
from .art_runtime import (
    require_runtime_registry,
    resolve_art_client,
    unload_llm_before_art,
)

router = APIRouter()
logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# Seed selection stays near the route entry point so callers keep the existing
# request contract while the runtime still receives one explicit seed value.


def resolve_seed_value(seed: Optional[int]) -> int:
    """Return the caller-provided seed or one random reproducible seed."""
    if seed is not None:
        return int(seed)
    return secrets.randbelow(2**31 - 1)


def _screen_request_input_image(request: GenerationRequest) -> None:
    """Screen one request's input image through the mandatory seam.

    Runs after the text gate and before any side effect. A text-only
    request skips the image gate; the trace line records which gate
    applied so a text-only pass is never mistaken for input-image
    coverage. Screening copies are dropped: decoding and screening must
    never preview or export the input.

    Raises:
        HTTPException: 400 when the input image is undecodable or the
            mandatory evaluator withholds it (blocked or unavailable).
    """
    if not request.image_b64:
        logger.info(
            "Input-image screen trace (path=api, text_gate=pass, "
            "input_images=0, image_gate=skipped_no_inputs)"
        )
        return
    try:
        decoded = decode_input_image(request.image_b64)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail=str(exc)
        ) from exc
    _outputs, _withheld, batch = check_images_mandatory([decoded])
    if batch.all_allowed:
        logger.info(
            "Input-image screen trace (path=api, text_gate=pass, "
            "input_images=1, image_gate=pass)"
        )
        return
    logger.warning(
        "Art generation request rejected by input-image screen "
        "(reason=%s)",
        ",".join(batch.reasons),
    )
    raise HTTPException(
        status_code=400,
        detail=rejection_message(
            ContentSafetyResult(
                allowed=False, reason=batch.reasons[0], field=None
            )
        ),
    )


async def create_generation_job(
    request: GenerationRequest,
    req: Request,
) -> str:
    """Create one tracked generation job and start its worker task."""
    # Content-safety input gate: reject policy-matching prompt text before
    # any side effect (LLM unload, job/tracker creation, model loading).
    # This early public-HTTP pre-check shares its validator with the
    # authoritative in-pipeline choke (manager _generate entries).
    gate_result = evaluate_prompt_fields(
        {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
        }
    )
    if not gate_result.allowed:
        logger.warning(
            "Art generation request rejected by content safety policy "
            "(reason=%s)",
            gate_result.reason,
        )
        raise HTTPException(
            status_code=400,
            detail=rejection_message(gate_result),
        )

    # Mandatory input-image screen (S10): an image-bearing request is
    # checked through the shared evaluator seam before model resolution
    # or any other side effect.
    _screen_request_input_image(request)

    # Model resolution runs before any side effect: a version with no
    # model resolves to an installed checkpoint, and a model that is
    # not available locally is rejected, so a bad request never
    # occupies the worker until the timeout (issue #2229).
    resolved_model = resolve_generation_model(request)
    client = resolve_art_client(require_runtime_registry(req))
    tracker = JobTracker()
    seed_value = resolve_seed_value(request.seed)
    # resolved_model is None only when the caller sent neither a model
    # nor a version, in which case the server default still applies.
    art_request = request.model_copy(
        update={"seed": seed_value, "model": resolved_model}
    )
    job_id = await tracker.create_art_job(
        metadata=build_generation_job_metadata(art_request, seed_value),
        capacity=1,
    )
    if job_id is None:
        raise HTTPException(
            status_code=503,
            detail="Art generation capacity is full; retry later",
            headers={"Retry-After": "1"},
        )
    tracker.bind_art_client(job_id, client)
    register_request = getattr(client, "register_request", None)
    request_registered = False
    runner_owns_reservation = False

    async def _cleanup_before_runner() -> None:
        finish_request = getattr(client, "finish_request", None)
        try:
            if request_registered and callable(finish_request):
                finish_request(job_id)
        finally:
            await tracker.discard_art_job(job_id)

    # Art generation owns one process-wide background slot, held through the
    # runner's actual terminal boundary. Coordinate the LLM handoff only after
    # admission so a rejected request has no model lifecycle side effects.
    try:
        if callable(register_request):
            register_request(job_id)
            request_registered = True
        await unload_llm_before_art(req, source="art_generate")
        if not await tracker.mark_art_job_running(job_id):
            finish_request = getattr(client, "finish_request", None)
            if request_registered and callable(finish_request):
                finish_request(job_id)
            await tracker.finish_art_job(job_id)
            runner_owns_reservation = True
            return job_id

        async def _run_reserved_job() -> None:
            try:
                await run_art_job(tracker, job_id, art_request, client)
            finally:
                finish_request = getattr(client, "finish_request", None)
                try:
                    if request_registered and callable(finish_request):
                        finish_request(job_id)
                finally:
                    await tracker.finish_art_job(job_id)

        task = asyncio.create_task(_run_reserved_job())
        tracker.attach_art_task(job_id, task, client)
        runner_owns_reservation = True
        return job_id
    finally:
        if not runner_owns_reservation:
            # The API request still owns the reservation until its runner is
            # attached. CancelledError is a BaseException, so this finally
            # covers cancellation during handoff and status/progress awaits.
            cleanup_task = asyncio.create_task(_cleanup_before_runner())
            try:
                await asyncio.shield(cleanup_task)
            except asyncio.CancelledError:
                await cleanup_task
                raise


@router.post("/generate", response_model=GenerationResponse)
async def generate_image(request: GenerationRequest, req: Request):
    """Start image generation and return the tracked job id."""
    # The route stays intentionally thin; the helper above owns the tracker,
    # runtime client, and task bootstrap so the API surface remains stable.
    logger.info("Image generation request (prompt_len=%s)", len(request.prompt))
    try:
        job_id = await create_generation_job(request, req)
        return GenerationResponse(job_id=job_id, status="running")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error starting generation: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Error starting generation: {exc}",
        ) from exc
