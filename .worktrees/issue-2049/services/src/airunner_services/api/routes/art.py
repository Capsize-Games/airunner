"""Art generation endpoints (Stable Diffusion).

Routes art generation through the daemon runtime registry.

NOTE: This module must work in headless/server mode.
"""

from fastapi import APIRouter

from .art_catalog_routes import router as catalog_router
from .catalog_bootstrap import router as catalog_bootstrap_router
from .art_contracts import (
    ArtComponentResponse,
    BackgroundRemovalRequest,
    GenerationRequest,
    GenerationResponse,
    JobStatusResponse,
    LocalArtModel,
    LocalArtModelsResponse,
    ModelInfo,
)
from .art_generation_routes import router as generation_router
from .art_management_routes import router as management_router

router = APIRouter()
router.include_router(generation_router)
router.include_router(management_router)
router.include_router(catalog_router)
router.include_router(catalog_bootstrap_router)
# The vram route module imports torch at module import time; the API server
# must be importable (and testable) in torch-free installs, so the router is
# attached lazily here (issue #2054).
try:
    from .vram import router as vram_router

    router.include_router(vram_router)
except ImportError as exc:
    # torch (or safetensors) is not installed; the VRAM endpoint is
    # unavailable but the rest of the API surface still serves.
    if exc.name not in {"torch", "safetensors"}:
        raise

__all__ = [
    "ArtComponentResponse",
    "BackgroundRemovalRequest",
    "GenerationRequest",
    "GenerationResponse",
    "JobStatusResponse",
    "LocalArtModel",
    "LocalArtModelsResponse",
    "ModelInfo",
    "router",
]
