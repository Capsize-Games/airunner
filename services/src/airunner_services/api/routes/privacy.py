"""Privacy consent / external-service toggle endpoint."""

from __future__ import annotations

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
    app = _app_settings()
    raw = app.privacy_service_consent or "{}" if app else "{}"
    import json
    try:
        services = json.loads(raw)
    except Exception:
        services = {}
    merged = {**_DEFAULT_SERVICES, **services}
    return {"services": merged}


@router.put("/privacy")
async def update_privacy(services: dict[str, bool]):
    """Update external-service consent toggles."""
    import json

    with session_scope() as session:
        app = _app_settings(session=session)
        if app is None:
            app = ApplicationSettings()
            session.add(app)
        app.privacy_service_consent = json.dumps(services)
        session.commit()
    return {"services": services}


def _app_settings(session=None):
    from airunner_services.database.session import session_scope

    if session is None:
        with session_scope() as s:
            return s.query(ApplicationSettings).first()
    return session.query(ApplicationSettings).first()
