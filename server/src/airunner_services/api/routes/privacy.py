"""Privacy consent / external-service toggle endpoint."""

from __future__ import annotations

import json

from fastapi import APIRouter

from airunner_services.database.models.application_settings import (
    ApplicationSettings,
)
from airunner_services.database.session import session_scope

router = APIRouter()

_DEFAULT_SERVICES: dict[str, bool] = {
    "huggingface": True,
    "civitai": True,
    "duckduckgo": True,
    "openmeteo": False,
    "openrouter": True,
    "openai": True,
}


@router.get("/privacy")
async def get_privacy():
    """Return the current external-service consent state."""
    with session_scope() as session:
        app = session.query(ApplicationSettings).first()
        raw = app.privacy_service_consent if app else "{}"
    try:
        services = json.loads(raw or "{}")
    except Exception:
        services = {}
    merged = {**_DEFAULT_SERVICES, **services}
    return {"services": merged}


@router.put("/privacy")
async def update_privacy(services: dict[str, bool]):
    """Update external-service consent toggles."""
    with session_scope() as session:
        app = session.query(ApplicationSettings).first()
        if app is None:
            app = ApplicationSettings()
            session.add(app)
        app.privacy_service_consent = json.dumps(services)
        session.commit()
    return {"services": services}
