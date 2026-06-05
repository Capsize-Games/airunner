"""API route modules — WebSocket-only architecture."""

from airunner_services.api.routes.events import router as events_router

__all__ = [
    "events_router",
]
