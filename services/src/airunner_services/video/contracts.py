"""Pydantic contracts for LTX video generation.

Bounds are validated here so malformed input is rejected before any
GPU side effect — never silently clamped (mirrors art_contracts.py).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

MAX_PROMPT_CHARS = 4000
MIN_DIMENSION = 256
MAX_DIMENSION = 1920
DIMENSION_MULTIPLE = 16  # pipeline pads to 32; 720p is 1280x720
MIN_FRAMES = 9
MAX_FRAMES = 241
FRAME_MODULUS = 8  # LTX temporal compression: frames == 1 (mod 8)
MIN_FPS = 1
MAX_FPS = 60
MIN_STEPS = 1
MAX_STEPS = 32  # distilled range
MAX_SEED = 2**31 - 1


def validate_frame_count(num_frames: int) -> int:
    """Return num_frames or raise unless it fits the LTX lattice."""
    if not MIN_FRAMES <= num_frames <= MAX_FRAMES:
        raise ValueError(
            f"num_frames must be {MIN_FRAMES}..{MAX_FRAMES}, "
            f"got {num_frames}"
        )
    if (num_frames - 1) % FRAME_MODULUS != 0:
        raise ValueError(
            f"num_frames must be 1 mod {FRAME_MODULUS} "
            f"(e.g. 81, 97, 121), got {num_frames}"
        )
    return num_frames


class VideoGenerationRequest(BaseModel):
    """Text-to-video (or image-to-video) generation request."""

    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_CHARS)
    negative_prompt: Optional[str] = Field(
        default="", max_length=MAX_PROMPT_CHARS
    )
    input_image_path: Optional[str] = None  # I2V first frame, host path
    width: int = Field(default=1280, ge=MIN_DIMENSION, le=MAX_DIMENSION)
    height: int = Field(default=720, ge=MIN_DIMENSION, le=MAX_DIMENSION)
    num_frames: int = 97
    fps: int = Field(default=24, ge=MIN_FPS, le=MAX_FPS)
    steps: int = Field(default=8, ge=MIN_STEPS, le=MAX_STEPS)
    seed: Optional[int] = Field(default=None, ge=0, le=MAX_SEED)
    audio: bool = True
    checkpoint: Literal["fp8", "nvfp4"] = "fp8"

    @field_validator("width", "height")
    @classmethod
    def _dimension_multiple(cls, value: int) -> int:
        if value % DIMENSION_MULTIPLE != 0:
            raise ValueError(
                f"dimensions must be multiples of "
                f"{DIMENSION_MULTIPLE}, got {value}"
            )
        return value

    @field_validator("num_frames")
    @classmethod
    def _frames_lattice(cls, value: int) -> int:
        return validate_frame_count(value)


class VideoJobStatus(BaseModel):
    """Status + telemetry for one video job."""

    job_id: str
    status: Literal[
        "queued", "running", "completed", "failed", "cancelled"
    ]
    progress: float = 0.0  # 0..1 across denoising steps
    error: Optional[str] = None
    wall_time_s: Optional[float] = None
    peak_vram_mb: Optional[float] = None
    peak_rss_mb: Optional[float] = None


class VideoModelInfo(BaseModel):
    """One installed checkpoint and its estimated 720p footprint."""

    checkpoint: str
    precision: str
    path: str
    installed: bool
    estimated_peak_vram_mb: Optional[float] = None
