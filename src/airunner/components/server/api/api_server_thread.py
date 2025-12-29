"""API Server Thread for headless mode.

Runs the headless HTTP API inside uvicorn/FastAPI.

We keep the legacy endpoints (/llm/*, /art, etc.) via a compatibility router
so existing clients continue to work.
"""

import threading

import uvicorn

from airunner.api.server import create_app
from airunner.components.server.api.server import get_api
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.settings import (
    AIRUNNER_HEADLESS_SERVER_HOST,
    AIRUNNER_HEADLESS_SERVER_PORT,
)

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class APIServerThread(threading.Thread):
    """Background thread running the AI Runner API server.

    Provides HTTP endpoints for LLM, art generation, TTS, and STT.
    Designed for headless operation without Qt GUI.

    Args:
        host: Host address to bind to (default: 0.0.0.0)
        port: Port to listen on (default: 8080)
    """

    def __init__(
        self,
        host: str = AIRUNNER_HEADLESS_SERVER_HOST,
        port: int = AIRUNNER_HEADLESS_SERVER_PORT,
    ):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server: uvicorn.Server | None = None
        self._stop_event = threading.Event()

    def run(self):
        """Start uvicorn and serve requests."""
        try:
            api = get_api()
            app = create_app(app_instance=api)

            logger.info(f"FastAPI server listening on http://{self.host}:{self.port}")
            logger.info("Available endpoints: /health, /llm/*, /art, /api/v1/*")

            config = uvicorn.Config(
                app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=True,
            )
            self.server = uvicorn.Server(config)
            self.server.run()

        except Exception as e:
            logger.error(f"API server error: {e}", exc_info=True)

    def stop(self):
        """Stop the server gracefully."""
        logger.info("Stopping API server...")
        self._stop_event.set()
        if self.server:
            self.server.should_exit = True
