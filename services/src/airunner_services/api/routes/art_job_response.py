"""Response handling for art job execution."""

import asyncio
import base64
from typing import List

from airunner_services.ipc.messages import EnvelopeStatus, RequestEnvelope
from airunner_services.runtimes.base import RuntimeClient
from airunner_services.utils.job_tracker import JobTracker

from .art_contracts import GenerationRequest
from .art_job_progress import fail_art_job, job_cancelled, progress_callback
from .art_job_requests import build_art_envelope
from .art_runtime import response_status_is


# Runtime response handling


async def invoke_art_request(
    client: RuntimeClient,
    envelope: RequestEnvelope,
    on_progress,
):
    """Invoke one art request, using progress callbacks when available."""
    invoke_with_progress = getattr(client, "invoke_with_progress", None)
    if callable(invoke_with_progress):
        return await asyncio.to_thread(
            invoke_with_progress,
            envelope,
            on_progress,
        )
    return await asyncio.to_thread(client.invoke, envelope)


def response_error_detail(response: object) -> str:
    """Return a normalized error detail from one art response."""
    error = getattr(response, "error", None)
    return getattr(error, "message", None) or "Art generation failed"


def response_images(response: object) -> List[str]:
    """Return every image payload from one art response, in batch order."""
    payload = getattr(response, "payload", None) or {}
    images = payload.get("images") or []
    if not images:
        raise ValueError("Art runtime returned no images")
    return images


def first_response_image(response: object) -> str:
    """Return the first image payload from one art response."""
    return response_images(response)[0]


def decode_response_images(response: object) -> List[bytes]:
    """Decode every image payload from one art response, in batch order."""
    try:
        return [
            base64.b64decode(image) for image in response_images(response)
        ]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Invalid image payload: {exc}") from exc


def decode_response_image(response: object) -> bytes:
    """Decode the first image payload from one art response."""
    return decode_response_images(response)[0]


async def apply_art_response(
    tracker: JobTracker,
    job_id: str,
    response: object,
) -> None:
    """Apply one art response to the tracked job state."""
    if response_status_is(response, EnvelopeStatus.CANCELLED):
        await tracker.cancel_job(job_id)
        return
    if response_status_is(response, EnvelopeStatus.FAILED):
        await fail_art_job(tracker, job_id, response_error_detail(response))
        return
    images_bytes = decode_response_images(response)
    if await job_cancelled(tracker, job_id):
        return
    # image_bytes (singular, first image) is kept for existing single-image
    # callers of GET /result/{job_id}; images_bytes (every checked batch
    # image) is the release-D03 addition consumed by the new indexed route
    # and the updated Desktop consumer.
    await tracker.complete_job(
        job_id,
        {"image_bytes": images_bytes[0], "images_bytes": images_bytes},
    )


async def run_art_job(
    tracker: JobTracker,
    job_id: str,
    request: GenerationRequest,
    client: RuntimeClient,
) -> None:
    """Execute one art runtime request and store the JobTracker result."""
    envelope = build_art_envelope(job_id, request)
    on_progress = progress_callback(asyncio.get_running_loop(), tracker, job_id)
    try:
        response = await invoke_art_request(client, envelope, on_progress)
    except Exception as exc:
        await fail_art_job(tracker, job_id, str(exc))
        return
    try:
        await apply_art_response(tracker, job_id, response)
    except Exception as exc:
        await fail_art_job(tracker, job_id, str(exc))