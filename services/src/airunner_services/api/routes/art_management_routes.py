"""Compatibility router for art control endpoints."""

from fastapi import APIRouter

from .art_background_routes import router as background_router
from .art_component_routes import router as component_router

router = APIRouter()
router.include_router(background_router)
router.include_router(component_router)