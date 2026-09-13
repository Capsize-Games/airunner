"""Pydantic models for art API routes."""

import base64
import os
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from airunner_services.art.config.image_generator_capabilities import (
    ImageGeneratorCapabilities,
)

# The shared default capability profile already used elsewhere (e.g.
# llm/tools/image_tools.py) as the fallback "unknown model" profile is
# reused here as the dimension bound source (release issue D04). Full
# per-request dynamic profile resolution (matching GenerationRequest's
# own model/version/pipeline fields to a specific generator) would need
# the daemon's ApplicationSettings.current_image_generator DB row, which
# is out of scope for this request-shape validation layer; using the
# shared default keeps the bound real and configurable rather than an
# arbitrary new constant, while remaining conservative for every model.
_DEFAULT_CAPABILITIES = ImageGeneratorCapabilities()
_MAX_PIXELS = _DEFAULT_CAPABILITIES.max_width * _DEFAULT_CAPABILITIES.max_height


def _max_steps() -> int:
    return int(os.environ.get("AIRUNNER_ART_MAX_STEPS", "150"))


def _max_batch_size() -> int:
    return int(os.environ.get("AIRUNNER_ART_MAX_BATCH_SIZE", "8"))


def _max_prompt_chars() -> int:
    return int(os.environ.get("AIRUNNER_ART_MAX_PROMPT_CHARS", "4000"))


def _max_image_bytes() -> int:
    """Maximum decoded (not base64-encoded) input-image size, in bytes."""
    return int(
        os.environ.get("AIRUNNER_ART_MAX_IMAGE_BYTES", str(25 * 1024 * 1024))
    )


class GenerationRequest(BaseModel):
    """Image generation request.

    Numeric and size bounds are validated here (release issue D04) so a
    negative, zero, excessive, non-finite, or malformed value is
    rejected before any tracker/model side effect — FastAPI validates
    the request body into this model before the route handler ever
    runs. Out-of-bounds values are rejected outright, never silently
    clamped, so a caller's request is never silently shrunk.
    """

    prompt: str = Field(..., min_length=1, max_length=_max_prompt_chars())
    negative_prompt: Optional[str] = Field(
        default="", max_length=_max_prompt_chars()
    )
    width: int = Field(
        default=_DEFAULT_CAPABILITIES.default_width,
        ge=_DEFAULT_CAPABILITIES.min_width,
        le=_DEFAULT_CAPABILITIES.max_width,
    )
    height: int = Field(
        default=_DEFAULT_CAPABILITIES.default_height,
        ge=_DEFAULT_CAPABILITIES.min_height,
        le=_DEFAULT_CAPABILITIES.max_height,
    )
    steps: int = Field(default=20, ge=1, le=_max_steps())
    # ge=0, not gt=0: Z-Image Turbo is documented to work best with
    # guidance_scale=0.0 (see zimage_generation_mixin.py), so 0 is a real,
    # supported value here rather than a meaningless edge case.
    cfg_scale: float = Field(
        default=7.5, ge=0, le=100.0, allow_inf_nan=False
    )
    seed: Optional[int] = None
    num_images: int = Field(default=1, ge=1, le=_max_batch_size())
    model: Optional[str] = None
    version: Optional[str] = None
    scheduler: Optional[str] = None
    pipeline: Optional[str] = None
    strength: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, allow_inf_nan=False
    )
    image_b64: Optional[str] = None
    skip_auto_export: bool = False

    @field_validator("image_b64")
    @classmethod
    def _validate_image_b64_size(cls, value: Optional[str]) -> Optional[str]:
        """Reject an input image whose decoded size exceeds the bound.

        Checked against the decoded byte size (not the base64 string
        length) so the actual payload the runtime would receive is what
        gets bounded.
        """
        if not value:
            return value
        try:
            decoded_size = len(base64.b64decode(value, validate=True))
        except Exception as exc:
            raise ValueError("image_b64 is not valid base64") from exc
        max_bytes = _max_image_bytes()
        if decoded_size > max_bytes:
            raise ValueError(
                f"Decoded input image ({decoded_size} bytes) exceeds the "
                f"maximum allowed size ({max_bytes} bytes)"
            )
        return value

    @model_validator(mode="after")
    def _validate_pixel_count(self) -> "GenerationRequest":
        """Bound total pixel count separately from each dimension.

        With today's single symmetric default profile (max_width ==
        max_height), any width/height pair that individually passes
        already satisfies this too, so it is not independently
        reachable yet. It becomes load-bearing the moment a per-model
        profile with an asymmetric max_width/max_height is wired in
        (e.g. a model capped wider than it is tall): a request could
        then pass both individual bounds while its product still
        exceeds a sane total pixel budget.
        """
        if self.width * self.height > _MAX_PIXELS:
            raise ValueError(
                f"Requested resolution {self.width}x{self.height} exceeds "
                f"the maximum pixel count ({_MAX_PIXELS})"
            )
        return self


class GenerationResponse(BaseModel):
    """Image generation response."""

    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    """Generation job status."""

    job_id: str
    status: str
    progress: float
    image_url: Optional[str] = None
    error: Optional[str] = None


class ModelInfo(BaseModel):
    """Art model information."""

    id: str
    name: str
    loaded: bool
    type: str


class LocalArtModel(BaseModel):
    """One local art model file."""

    id: str
    name: str
    path: str
    size_bytes: int


class LocalArtModelsResponse(BaseModel):
    """Response payload for local art models."""

    base_dir: str
    models: List[LocalArtModel]


class BackgroundRemovalRequest(BaseModel):
    """Background-removal request payload."""

    image_b64: str


class ArtComponentResponse(BaseModel):
    """Art component control response."""

    component: str
    status: str


__all__ = [
    "ArtComponentResponse",
    "BackgroundRemovalRequest",
    "GenerationRequest",
    "GenerationResponse",
    "JobStatusResponse",
    "LocalArtModel",
    "LocalArtModelsResponse",
    "ModelInfo",
]