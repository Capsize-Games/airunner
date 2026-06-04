"""Legacy compatibility routes for synchronous art generation."""

import base64
import io
import threading
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Request

from airunner_services.contract_enums import SignalCode
from airunner_services.utils.application.signal_mediator import SignalMediator

from .legacy_common import get_airunner_app
from .legacy_contracts import LegacyArtRequest

router = APIRouter()


def _resolve_legacy_art_params(body: LegacyArtRequest) -> dict:
    """Extract and normalize parameters from the legacy art request."""
    prompt = (body.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing 'prompt' field")
    cfg_scale = (
        float(body.cfg_scale)
        if body.cfg_scale is not None
        else float(body.scale) if body.scale is not None else 7.5
    )
    want_random = (
        bool(body.random_seed)
        if body.random_seed is not None
        else body.seed is None
    )
    seed = None if want_random else (
        int(body.seed) if body.seed is not None else None
    )
    num_images = max(1, int(body.n_samples or 1))
    return {
        "prompt": prompt,
        "negative_prompt": body.negative_prompt or "",
        "width": int(body.width),
        "height": int(body.height),
        "steps": int(body.steps),
        "cfg_scale": float(cfg_scale),
        "seed": seed,
        "num_images": int(num_images),
    }


def _setup_signal_handlers(
    num_images: int,
) -> tuple[
    SignalMediator,
    threading.Event,
    dict[str, str],
    list[Any],
    Callable[[dict], None],
    Callable[[dict], None],
]:
    """Wire signal handlers and return mediator state collection."""
    mediator = SignalMediator()
    done = threading.Event()
    error_holder: dict[str, str] = {"error": ""}
    images: list[Any] = []

    def on_image_generated(data: dict) -> None:
        image = data.get("image")
        if image is not None:
            images.append(image)
        if len(images) >= num_images:
            done.set()

    def on_error(data: dict) -> None:
        error_holder["error"] = str(
            data.get("message") or "Unknown error"
        )
        done.set()

    mediator.register(
        SignalCode.SD_IMAGE_GENERATED_SIGNAL, on_image_generated
    )
    mediator.register(SignalCode.APPLICATION_ERROR_SIGNAL, on_error)
    return (
        mediator,
        done,
        error_holder,
        images,
        on_image_generated,
        on_error,
    )


def _cleanup_signal_handlers(
    mediator: SignalMediator,
    on_image_generated: Callable[[dict], None],
    on_error: Callable[[dict], None],
) -> None:
    """Best-effort unregister of signal handlers."""
    try:
        mediator.unregister(
            SignalCode.SD_IMAGE_GENERATED_SIGNAL,
            on_image_generated,
        )
        mediator.unregister(SignalCode.APPLICATION_ERROR_SIGNAL, on_error)
    except Exception:
        pass


def _encode_images_as_base64(images: list[Any]) -> list[str]:
    """Convert PIL images to base64-encoded PNG strings."""
    encoded: list[str] = []
    for image in images:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded.append(
            base64.b64encode(buffer.getvalue()).decode("utf-8")
        )
    return encoded


@router.post("/art")
def legacy_art_generate(body: LegacyArtRequest, req: Request):
    """Serve the legacy synchronous art endpoint."""
    _ = get_airunner_app(req)
    params = _resolve_legacy_art_params(body)
    (
        mediator,
        done,
        error_holder,
        images,
        on_image_generated,
        on_error,
    ) = _setup_signal_handlers(params["num_images"])
    try:
        mediator.emit_signal(
            SignalCode.SD_GENERATE_IMAGE_SIGNAL, params
        )
        if not done.wait(timeout=300):
            raise HTTPException(
                status_code=504, detail="Image generation timeout"
            )
        if error_holder["error"]:
            raise HTTPException(
                status_code=500, detail=error_holder["error"]
            )
        if not images:
            raise HTTPException(
                status_code=500, detail="No image returned"
            )
        encoded = _encode_images_as_base64(images)
        return {
            "images": encoded,
            "metadata": {},
            "seed": body.seed,
            "summary": "Generated image(s) returned as base64 strings.",
        }
    finally:
        _cleanup_signal_handlers(
            mediator, on_image_generated, on_error
        )
