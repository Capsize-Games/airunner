"""API route modules."""

from airunner_services.api.routes import (
    art,
    canvas_image,
    conversations,
    daemon,
    downloads,
    health,
    knowledge_base,
    legacy,
    llm,
    persistence,
    stt,
    tts,
)
from airunner_services.api.routes.art_options import router as art_options_router
from airunner_services.api.routes.embeddings import router as embeddings_router
from airunner_services.api.routes.layers import router as layers_router

__all__ = [
    "art",
    "art_options_router",
    "canvas_image",
    "conversations",
    "daemon",
    "downloads",
    "embeddings_router",
    "health",
    "knowledge_base",
    "layers_router",
    "legacy",
    "llm",
    "persistence",
    "stt",
    "tts",
]
