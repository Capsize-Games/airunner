"""Local validation for video MCP payloads (daemon re-validates).

Bounds mirror video/contracts.py so bad input fails in the MCP
process before any HTTP side effect.
"""

from __future__ import annotations

from typing import Any

from airunner_services.video.contracts import (
    DIMENSION_MULTIPLE,
    MAX_DIMENSION,
    MAX_FPS,
    MAX_FRAMES,
    MAX_PROMPT_CHARS,
    MAX_SEED,
    MAX_STEPS,
    MIN_DIMENSION,
    MIN_FPS,
    MIN_FRAMES,
    MIN_STEPS,
)


def build_video_payload(
    prompt: str,
    width: int = 1280,
    height: int = 720,
    num_frames: int = 97,
    fps: int = 24,
    steps: int = 8,
    seed: int | None = None,
    input_image_path: str | None = None,
    checkpoint: str = "fp8",
    audio: bool = True,
) -> dict[str, Any]:
    """Validate inputs and return the daemon request body."""
    text = (prompt or "").strip()
    if not 1 <= len(text) <= MAX_PROMPT_CHARS:
        raise ValueError(f"prompt must be 1..{MAX_PROMPT_CHARS} chars")
    for name, value in (("width", width), ("height", height)):
        if not MIN_DIMENSION <= value <= MAX_DIMENSION:
            raise ValueError(f"{name} out of range: {value}")
        if value % DIMENSION_MULTIPLE != 0:
            raise ValueError(f"{name} must be a multiple of 16")
    if not MIN_FRAMES <= num_frames <= MAX_FRAMES:
        raise ValueError(f"num_frames out of range: {num_frames}")
    if (num_frames - 1) % 8 != 0:
        raise ValueError("num_frames must be 1 mod 8 (81, 97, 121…)")
    if not MIN_FPS <= fps <= MAX_FPS:
        raise ValueError(f"fps out of range: {fps}")
    if not MIN_STEPS <= steps <= MAX_STEPS:
        raise ValueError(f"steps out of range: {steps}")
    if seed is not None and not 0 <= seed <= MAX_SEED:
        raise ValueError(f"seed out of range: {seed}")
    if checkpoint not in ("fp8", "nvfp4"):
        raise ValueError('checkpoint must be "fp8" or "nvfp4"')
    return {
        "prompt": text,
        "width": width,
        "height": height,
        "num_frames": num_frames,
        "fps": fps,
        "steps": steps,
        "seed": seed,
        "input_image_path": input_image_path,
        "checkpoint": checkpoint,
        "audio": audio,
    }
