"""Pydantic models for art API routes."""

from typing import List, Optional

from pydantic import BaseModel


class GenerationRequest(BaseModel):
    """Image generation request."""

    prompt: str
    negative_prompt: Optional[str] = ""
    width: int = 1024
    height: int = 1024
    steps: int = 20
    cfg_scale: float = 7.5
    seed: Optional[int] = None
    num_images: int = 1
    model: Optional[str] = None
    version: Optional[str] = None
    scheduler: Optional[str] = None
    pipeline: Optional[str] = None
    strength: Optional[float] = None
    image_b64: Optional[str] = None
    mask_image_b64: Optional[str] = None
    skip_auto_export: bool = False


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
    image: Optional[str] = None
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
