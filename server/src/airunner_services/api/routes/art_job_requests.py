"""Request builders for art job execution."""

from airunner_services.ipc.messages import RequestEnvelope
from airunner_services.runtimes.contracts import (
    ArtInvocationRequest,
    RuntimeAction,
    RuntimeKind,
)

from .art_contracts import GenerationRequest

# Request payload assembly


def build_generation_job_metadata(
    request: GenerationRequest,
    seed_value: int,
) -> dict:
    """Return JobTracker metadata for one generation request."""
    return {
        "prompt": request.prompt,
        "negative_prompt": request.negative_prompt,
        "width": request.width,
        "height": request.height,
        "steps": request.steps,
        "cfg_scale": request.cfg_scale,
        "seed": seed_value,
        "num_images": request.num_images,
        "model": request.model,
        "version": request.version,
        "scheduler": request.scheduler,
        "has_image_b64": request.image_b64 is not None,
        "has_mask_image_b64": request.mask_image_b64 is not None,
    }


def build_request_metadata(request: GenerationRequest) -> dict:
    """Return runtime metadata for one generation request."""
    metadata = {}
    if request.version:
        metadata["version"] = request.version
    if request.scheduler:
        metadata["scheduler"] = request.scheduler
    if request.pipeline:
        metadata["pipeline"] = request.pipeline
    if request.strength is not None:
        metadata["strength"] = float(request.strength)
    if request.image_b64:
        metadata["image_b64"] = request.image_b64
    if request.mask_image_b64:
        metadata["mask_image_b64"] = request.mask_image_b64
    if request.skip_auto_export:
        metadata["skip_auto_export"] = True
    return metadata


def build_art_payload(request: GenerationRequest) -> dict:
    """Return the art invocation payload for one generation request."""
    return ArtInvocationRequest(
        prompt=request.prompt,
        negative_prompt=request.negative_prompt or "",
        model=request.model,
        width=request.width,
        height=request.height,
        steps=request.steps,
        cfg_scale=request.cfg_scale,
        seed=request.seed,
        num_images=request.num_images,
        metadata=build_request_metadata(request),
    ).model_dump()


def build_art_envelope(
    job_id: str,
    request: GenerationRequest,
) -> RequestEnvelope:
    """Return the art invocation envelope for one generation job."""
    return RequestEnvelope(
        request_id=job_id,
        runtime=RuntimeKind.ART,
        action=RuntimeAction.INVOKE,
        provider="local",
        payload=build_art_payload(request),
    )
