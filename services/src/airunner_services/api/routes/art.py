"""Art generation endpoints (Stable Diffusion).

Routes art generation through the daemon runtime registry.

NOTE: This module must work in headless/server mode.
"""

from fastapi import APIRouter

from .art_catalog_routes import router as catalog_router
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
