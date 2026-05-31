"""Compatibility router for art generation endpoints."""

from fastapi import APIRouter

from .art_generation_job_routes import router as job_router
from .art_generation_start_routes import router as start_router

router = APIRouter()
router.include_router(start_router)
router.include_router(job_router)