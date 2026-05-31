"""Background-removal routes for art API endpoints."""

import base64

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from airunner_services.runtimes.contracts import RuntimeAction

from .art_contracts import BackgroundRemovalRequest
from .art_runtime import invoke_art_control

router = APIRouter()


# Background removal returns the first PNG payload directly because callers do
# not need the broader runtime envelope once the image has been decoded.


def background_png_bytes(response: object) -> bytes:
    """Return the decoded PNG payload from one background-removal response."""
    payload = getattr(response, "payload", None) or {}
    images = payload.get("images") or []
    if not images:
        raise HTTPException(
            status_code=500,
            detail="Background removal produced no image output",
        )
    try:
        return base64.b64decode(images[0])
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid background removal payload: {exc}",
        ) from exc


def background_request_payload(image_b64: str) -> dict:
    """Return the runtime payload for one background-removal request."""
    return {"prompt": "", "metadata": {"image_b64": image_b64}}


@router.post("/remove-background")
async def remove_background(
    request: BackgroundRemovalRequest,
    req: Request,
):
    """Remove the background from one input image through the runtime."""
    response = await invoke_art_control(
        req,
        action=RuntimeAction.INVOKE,
        payload=background_request_payload(request.image_b64),
        metadata={"operation": "remove_background"},
    )
    return Response(
        content=background_png_bytes(response),
        media_type="image/png",
    )