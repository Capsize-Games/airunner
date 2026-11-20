"""Validation and payload building for generation requests.

Bounds mirror the daemon's ``GenerationRequest`` (see
``api/routes/art_contracts.py``) so invalid input fails in the MCP
process before any HTTP side effect. The daemon still re-validates;
these checks are a fast local fail, not the authority.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

MIN_PROMPT_CHARS = 1
MAX_PROMPT_CHARS = 4000
MIN_DIMENSION = 64
MAX_DIMENSION = 2048
MIN_STEPS = 1
MAX_STEPS = 150
MIN_CFG_SCALE = 0.0
MAX_CFG_SCALE = 100.0
MIN_IMAGES = 1
MAX_IMAGES = 8
MIN_STRENGTH = 0.0
MAX_STRENGTH = 1.0
MAX_SEED = 2**31 - 1
LOCAL_PROVIDER = "local"
MUSE_PROVIDER = "muse"


def validate_prompt(prompt: str) -> str:
    """Return the stripped prompt or raise when it is unusable."""
    text = (prompt or "").strip()
    if not MIN_PROMPT_CHARS <= len(text) <= MAX_PROMPT_CHARS:
        raise ValueError(
            f"prompt must be {MIN_PROMPT_CHARS}..{MAX_PROMPT_CHARS} "
            f"characters, got {len(text)}"
        )
    return text


def validate_dimensions(width: int, height: int) -> tuple[int, int]:
    """Return validated dimensions or raise outside daemon bounds."""
    for name, value in (("width", width), ("height", height)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{name} must be an integer")
        if not MIN_DIMENSION <= value <= MAX_DIMENSION:
            raise ValueError(
                f"{name} must be {MIN_DIMENSION}..{MAX_DIMENSION}, "
                f"got {value}"
            )
    return width, height


def validate_options(
    steps: int,
    cfg_scale: float,
    num_images: int,
    seed: int | None,
    strength: float | None,
    provider: str,
) -> None:
    """Raise when any generation option leaves daemon bounds."""
    if not MIN_STEPS <= steps <= MAX_STEPS:
        raise ValueError(f"steps must be {MIN_STEPS}..{MAX_STEPS}")
    if not MIN_CFG_SCALE <= cfg_scale <= MAX_CFG_SCALE:
        raise ValueError(
            f"cfg_scale must be {MIN_CFG_SCALE}..{MAX_CFG_SCALE}"
        )
    if not MIN_IMAGES <= num_images <= MAX_IMAGES:
        raise ValueError(f"num_images must be {MIN_IMAGES}..{MAX_IMAGES}")
    if seed is not None and not 0 <= seed <= MAX_SEED:
        raise ValueError(f"seed must be 0..{MAX_SEED}")
    if strength is not None and not MIN_STRENGTH <= strength <= MAX_STRENGTH:
        raise ValueError(
            f"strength must be {MIN_STRENGTH}..{MAX_STRENGTH}"
        )
    if provider not in (LOCAL_PROVIDER, MUSE_PROVIDER):
        raise ValueError('provider must be "local" or "muse"')


def load_input_image_b64(path: str) -> str:
    """Return base64 input bytes for img2img or raise when unreadable."""
    target = Path(path).expanduser()
    if not target.is_file():
        raise ValueError(f"input image not found: {path}")
    return base64.b64encode(target.read_bytes()).decode("ascii")


def build_generation_payload(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    steps: int = 9,
    cfg_scale: float = 0.0,
    seed: int | None = None,
    num_images: int = 1,
    model: str | None = None,
    version: str | None = None,
    scheduler: str | None = None,
    provider: str = LOCAL_PROVIDER,
    input_image_path: str | None = None,
    strength: float | None = None,
) -> dict[str, Any]:
    """Validate arguments and return the daemon request body.

    Defaults target Z-Image Turbo (the daemon's default art model):
    single detailed prompt, guidance ``0.0``, and ~9 steps. The
    daemon resolves ``model``/``version`` when omitted.
    """
    text = validate_prompt(prompt)
    width, height = validate_dimensions(width, height)
    validate_options(steps, cfg_scale, num_images, seed, strength, provider)
    payload: dict[str, Any] = {
        "provider": provider,
        "prompt": text,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "num_images": num_images,
    }
    if seed is not None:
        payload["seed"] = seed
    if model:
        payload["model"] = model
    if version:
        payload["version"] = version
    if scheduler:
        payload["scheduler"] = scheduler
    if strength is not None:
        payload["strength"] = strength
    if input_image_path:
        payload["image_b64"] = load_input_image_b64(input_image_path)
    return payload
