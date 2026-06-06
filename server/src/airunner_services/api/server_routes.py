"""Route registration helper extracted from server_helpers.py."""

from __future__ import annotations

from fastapi import FastAPI


def _collect_routers():
    """Lazy-import all route modules and return their routers."""
    from airunner_services.api.routes import events_router
    from airunner_services.api.routes.health import router as health_router
    from airunner_services.api.routes.art_daemon_ws import (
        router as art_daemon_ws_router,
    )
    from airunner_services.api.routes.art_websocket import (
        router as art_ws_router,
    )
    from airunner_services.api.routes.images import (
        router as images_router,
    )
    from airunner_services.api.routes.llm_stream_routes import (
        router as llm_ws_router,
    )
    from airunner_services.api.routes.tts import router as tts_router
    from airunner_services.api.routes.hardware import (
        router as hardware_ws_router,
    )
    from airunner_services.api.routes.geolocation import (
        router as geolocation_router,
    )
    from airunner_services.api.routes.canvas_document import (
        router as canvas_ws_router,
    )

    return (
        health_router,
        events_router,
        art_ws_router,
        art_daemon_ws_router,
        llm_ws_router,
        tts_router,
        hardware_ws_router,
        geolocation_router,
        canvas_ws_router,
        images_router,
    )


def register_routes(app: FastAPI) -> None:
    """Register all API route handlers."""
    (
        health_router,
        events_router,
        art_ws_router,
        art_daemon_ws_router,
        llm_ws_router,
        tts_router,
        hardware_ws_router,
        geolocation_router,
        canvas_ws_router,
        images_router,
    ) = _collect_routers()
    app.include_router(health_router, prefix="/api/v1", tags=["health"])
    app.include_router(events_router, prefix="/api/v1", tags=["events"])
    app.include_router(art_ws_router, prefix="/api/v1/art", tags=["art"])
    app.include_router(llm_ws_router, prefix="/api/v1/llm", tags=["llm"])
    app.include_router(tts_router, prefix="/api/v1/tts", tags=["tts"])
    app.include_router(
        hardware_ws_router,
        prefix="/api/v1/daemon",
        tags=["daemon"],
    )
    app.include_router(
        geolocation_router,
        prefix="/api/v1/daemon",
        tags=["daemon"],
    )
    app.include_router(
        art_daemon_ws_router,
        prefix="/api/v1/art",
        tags=["art"],
    )
    app.include_router(
        canvas_ws_router,
        prefix="/api/v1/canvas",
        tags=["canvas"],
    )
    app.include_router(
        images_router,
        prefix="/api/v1/art",
        tags=["art"],
    )
