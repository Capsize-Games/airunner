"""Art request metadata resolution for local fallback."""

from __future__ import annotations

import base64
import io
import json
from typing import Any

from PIL import Image


def _resolve_art_request_version(metadata: dict[str, Any]) -> str:
    """Return the model version carried by one art invocation."""
    from airunner_common.contract_enums import normalize_art_version

    version = str(metadata.get("version") or "").strip()
    if version:
        return normalize_art_version(version)
    from airunner_common.contract_enums import DEFAULT_ART_VERSION

    return DEFAULT_ART_VERSION.value


def _resolve_art_request_scheduler(metadata: dict[str, Any]) -> str:
    """Return the scheduler carried by one art invocation."""
    scheduler = str(metadata.get("scheduler") or "").strip()
    if scheduler:
        return scheduler

    from airunner_common.settings import AIRUNNER_DEFAULT_SCHEDULER

    return AIRUNNER_DEFAULT_SCHEDULER


def _resolve_art_pipeline_action(metadata: dict[str, Any]) -> str:
    """Return the requested art pipeline action."""
    pipeline_action = str(metadata.get("pipeline") or "").strip()
    if pipeline_action:
        return pipeline_action
    return "txt2img"


def _resolve_art_generator_section(metadata: dict[str, Any]) -> Any:
    """Return the requested generator section for one art job."""
    from airunner_common.contract_enums import GeneratorSection

    pipeline_action = _resolve_art_pipeline_action(metadata)
    try:
        return GeneratorSection(pipeline_action)
    except ValueError:
        return GeneratorSection.TXT2IMG


def _resolve_art_request_strength(metadata: dict[str, Any]) -> float:
    """Return one normalized strength value for image-conditioned jobs."""
    try:
        return float(metadata.get("strength"))
    except (TypeError, ValueError):
        return 0.5


def _decode_art_metadata_image(encoded_image: Any) -> Any:
    """Return one decoded PIL image from art request metadata."""
    if not encoded_image:
        return None
    try:
        image_bytes = base64.b64decode(encoded_image)
        with Image.open(io.BytesIO(image_bytes)) as image:
            return image.convert("RGB")
    except Exception:
        return None


def _resolve_art_request_image(metadata: dict[str, Any]) -> Any:
    """Return one decoded PIL image carried by the art invocation."""
    return _decode_art_metadata_image(metadata.get("image_b64"))


def _resolve_art_request_mask(metadata: dict[str, Any]) -> Any:
    """Return one decoded mask image carried by the art invocation."""
    return _decode_art_metadata_image(metadata.get("mask_b64"))


def _resolve_art_request_outpaint_mask_blur(
    metadata: dict[str, Any],
) -> int:
    """Return the requested outpaint blur radius."""
    try:
        return int(metadata.get("outpaint_mask_blur") or 0)
    except (TypeError, ValueError):
        return 0


def _resolve_art_active_rect(metadata: dict[str, Any]) -> Any:
    """Return one decoded active rectangle for outpaint requests."""
    raw_rect = metadata.get("active_rect")
    if not raw_rect:
        return None

    if isinstance(raw_rect, str):
        try:
            raw_rect = json.loads(raw_rect)
        except ValueError:
            return None

    if not isinstance(raw_rect, dict):
        return None

    try:
        from airunner_services.art.managers.stablediffusion.rect import Rect

        return Rect(
            int(raw_rect.get("x", 0)),
            int(raw_rect.get("y", 0)),
            int(raw_rect.get("width", 0)),
            int(raw_rect.get("height", 0)),
        )
    except Exception:
        return None


def _resolve_art_operation(metadata: dict[str, Any]) -> str:
    """Return the requested art operation."""
    operation = str(metadata.get("operation") or "generate").strip()
    return operation or "generate"
