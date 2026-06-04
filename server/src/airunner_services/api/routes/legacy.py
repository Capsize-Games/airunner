"""Legacy/compatibility endpoints.

Some existing consumers historically talk to the headless server using:
- GET  /health
- GET  /llm/models
- POST /llm/generate  (streams NDJSON)
- POST /art           (sync, returns base64 PNGs)
- POST /admin/*

When running headless under FastAPI/uvicorn, we keep these endpoints so the
rest of the stack doesn't need a coordinated flag-day migration.
"""

from fastapi import APIRouter

from .legacy_admin_routes import router as admin_router
from .legacy_art_routes import router as art_router
from .legacy_contracts import (
    LegacyArtRequest,
    LegacyInterruptRequest,
    LegacyLLMGenerateRequest,
)
from .legacy_llm_routes import router as llm_router
from .legacy_status_routes import router as status_router

router = APIRouter()
router.include_router(status_router)
router.include_router(llm_router)
router.include_router(art_router)
router.include_router(admin_router)

__all__ = [
    "LegacyArtRequest",
    "LegacyInterruptRequest",
    "LegacyLLMGenerateRequest",
    "router",
]
