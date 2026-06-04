"""Art request handlers extracted from the legacy HTTP server."""

from __future__ import annotations

import base64
import io
import os
import threading
from typing import Any, Callable

from airunner_services.art.managers.stablediffusion.image_response import (
    ImageResponse,
)
from airunner_services.art.managers.stablediffusion.image_request import (
    ImageRequest,
)
from airunner_services.contract_enums import GeneratorSection, SignalCode


def handle_art(
    handler: Any,
    data: dict[str, Any],
    *,
    get_api: Callable[..., Any],
) -> None:
    """Handle the general /art generation endpoint."""
    success, error_msg = handler._ensure_art_model_loaded()
    if not success:
        _send_art_model_unavailable(handler, error_msg)
        return
    prompt = data.get("prompt", "")
    if not prompt:
        handler._send_json_response({"error": "Missing 'prompt' field"}, status=400)
        return
    complete_event = threading.Event()
    result_holder = {"response": None, "error": None}
    image_request = create_image_request(data)
    image_request.callback = completion_callback(handler, result_holder, complete_event)
    api = get_api()
    if not api:
        handler._send_json_response({"error": "API not initialized"}, status=500)
        return
    _dispatch_art_request(handler, api, prompt, image_request)
    _handle_art_response(handler, result_holder, complete_event)


def create_image_request(data: dict[str, Any]) -> ImageRequest:
    """Create an ImageRequest from HTTP request data."""
    image_request = ImageRequest(
        prompt=data.get("prompt", ""),
        negative_prompt=data.get("negative_prompt", ""),
        second_prompt=data.get("second_prompt", ""),
        second_negative_prompt=data.get("second_negative_prompt", ""),
        width=data.get("width", 1024),
        height=data.get("height", 1024),
        steps=data.get("steps", 20),
        seed=data.get("seed", 42),
        scale=data.get("scale", 7.5),
        random_seed=data.get("random_seed", True),
        n_samples=data.get("n_samples", 1),
        images_per_batch=data.get("images_per_batch", 1),
        generator_section=GeneratorSection.TXT2IMG,
        pipeline_action="txt2img",
    )
    model_path = data.get("model_path") or os.environ.get("AIRUNNER_ART_MODEL_PATH")
    if model_path:
        image_request.model_path = model_path
    return image_request


def format_art_response(handler: Any, response: Any) -> dict[str, Any]:
    """Format one art generation response for HTTP JSON output."""
    images, metadata, seed = response_parts(response)
    images_base64 = encoded_images(handler, images)
    return {
        "images": images_base64,
        "metadata": response_metadata(metadata),
        "seed": seed,
        "count": len(images_base64),
    }


def _send_art_model_unavailable(handler: Any, error_msg: str) -> None:
    """Send the standard unavailable-art-model response."""
    handler._send_json_response(
        {
            "error": "Art model not available",
            "details": error_msg,
            "hint": "Start with --enable-art --art-model flag or configure in AIRunner GUI",
        },
        status=503,
    )


def completion_callback(
    handler: Any,
    result_holder: dict[str, Any],
    complete_event: threading.Event,
) -> Callable[[Any], None]:
    """Return the art completion callback."""
    def on_complete(response: Any) -> None:
        handler.logger.info("Art generation callback received: %s", type(response))
        if isinstance(response, str):
            result_holder["error"] = response
        else:
            result_holder["response"] = response
        complete_event.set()

    return on_complete


def _dispatch_art_request(
    handler: Any,
    api: Any,
    prompt: str,
    image_request: ImageRequest,
) -> None:
    """Dispatch one art request through the shared API signal path."""
    handler.logger.info("Sending art generation request (prompt_len=%s)", len(prompt))
    api.emit_signal(SignalCode.DO_GENERATE_SIGNAL, {"image_request": image_request})


def _handle_art_response(
    handler: Any,
    result_holder: dict[str, Any],
    complete_event: threading.Event,
) -> None:
    """Translate the art callback result into one HTTP response."""
    if not complete_event.wait(timeout=300):
        handler._send_json_response(
            {
                "error": "Image generation timeout",
                "hint": "Generation took longer than 5 minutes",
            },
            status=504,
        )
        return
    if result_holder["error"]:
        handler._send_json_response({"error": result_holder["error"]}, status=500)
        return
    if not result_holder["response"]:
        handler._send_json_response({"error": "No response received"}, status=500)
        return
    handler._send_json_response(format_art_response(handler, result_holder["response"]))


def response_parts(response: Any) -> tuple[list[Any], dict[str, Any], Any]:
    """Return images, metadata, and seed for one art response object."""
    if isinstance(response, ImageResponse):
        metadata = response.data or {}
        return response.images or [], metadata, response_seed(metadata)
    if isinstance(response, dict):
        metadata = response.get("data", {})
        return response.get("images", []), metadata, metadata.get("seed")
    return [], {}, None


def response_seed(metadata: dict[str, Any]) -> Any:
    """Return the seed stored in one art response metadata payload."""
    image_request = metadata.get("image_request")
    if image_request and hasattr(image_request, "seed"):
        return image_request.seed
    return None


def encoded_images(handler: Any, images: list[Any]) -> list[str]:
    """Encode the image list from one art response to base64 strings."""
    encoded: list[str] = []
    for image in images:
        if image is None:
            continue
        payload = encode_image(handler, image)
        if payload:
            encoded.append(payload)
    return encoded


def encode_image(handler: Any, image: Any) -> str:
    """Encode one image to a base64 PNG string."""
    try:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as error:
        handler.logger.error("Failed to encode image: %s", error)
        return ""


def response_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return the metadata subset exposed by the legacy art endpoint."""
    if not metadata:
        return {}
    return {
        "width": metadata.get("width"),
        "height": metadata.get("height"),
        "steps": metadata.get("steps"),
        "prompt": metadata.get("prompt"),
    }