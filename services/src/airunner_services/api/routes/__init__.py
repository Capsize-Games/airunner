"""API route modules."""

from airunner_services.api.routes import (
    art,
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
from airunner_services.api.routes.canvas_document import (
    router as canvas_document_router,
)
from airunner_services.api.routes.embeddings import router as embeddings_router
from airunner_services.api.routes.embeddings_watch import (
    router as embeddings_watch_router,
)
from airunner_services.api.routes.images import router as images_router
from airunner_services.api.routes.knowledge_base_index import (
    router as knowledge_base_index_router,
)
from airunner_services.api.routes.knowledge_base_watch import (
    router as knowledge_base_watch_router,
)
from airunner_services.api.routes.lora_watch import router as lora_watch_router
from airunner_services.api.routes.models_status import router as models_status_router
from airunner_services.api.routes.models_watch import router as models_watch_router
from airunner_services.api.routes.privacy import router as privacy_router

__all__ = [
    "art",
    "art_options_router",
    "canvas_document_router",
    "conversations",
    "daemon",
    "downloads",
    "embeddings_router",
    "embeddings_watch_router",
    "health",
    "images_router",
    "knowledge_base",
    "knowledge_base_index_router",
    "knowledge_base_watch_router",
    "legacy",
    "llm",
    "lora_watch_router",
    "models_status_router",
    "models_watch_router",
    "persistence",
    "privacy_router",
    "stt",
    "tts",
]
