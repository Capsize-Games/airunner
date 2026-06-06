"""API route modules — WebSocket-only architecture."""

from airunner_services.api.routes import events as _events  # noqa: F401
from airunner_services.api.routes import rpc_handlers as _rpc  # noqa: F401
from airunner_services.api.routes import rpc_art  # noqa: F401
from airunner_services.api.routes import rpc_canvas  # noqa: F401
from airunner_services.api.routes import rpc_downloads  # noqa: F401
from airunner_services.api.routes import rpc_embeddings  # noqa: F401
from airunner_services.api.routes import rpc_images  # noqa: F401
from airunner_services.api.routes import rpc_kb  # noqa: F401
from airunner_services.api.routes import rpc_loras  # noqa: F401
from airunner_services.api.routes import rpc_models  # noqa: F401
from airunner_services.api.routes import rpc_privacy  # noqa: F401
from airunner_services.api.routes import rpc_settings  # noqa: F401

from airunner_services.api.routes.events import router as events_router

__all__ = [
    "events_router",
]
