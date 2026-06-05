"""API Server Thread for service mode.

Runs the HTTP API inside uvicorn/FastAPI.
"""

import threading

import os

import uvicorn

from airunner_services.api.server import (
    access_logs_enabled,
    create_app,
    is_loopback_host,
)
from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger
from airunner_services.settings import (
    AIRUNNER_HEADLESS_SERVER_HOST,
    AIRUNNER_HEADLESS_SERVER_PORT,
)

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class APIServerThread(threading.Thread):
    """Background thread running the AI Runner API server.

    Provides HTTP endpoints for LLM, art generation, TTS, and STT.
    Designed for operation without Qt GUI.

    Args:
        host: Host address to bind to (default: localhost)
        port: Port to listen on (default: 8080)
        app_instance: Optional AIRunner app instance for dependency injection
    """

    def __init__(
        self,
        host: str = AIRUNNER_HEADLESS_SERVER_HOST,
        port: int = AIRUNNER_HEADLESS_SERVER_PORT,
        app_instance=None,
    ):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.app_instance = app_instance
        self.server: uvicorn.Server | None = None
        self._stop_event = threading.Event()

    def run(self):
        """Start uvicorn and serve requests."""
        try:
            api_key = (os.environ.get("AIRUNNER_API_KEY") or "").strip()
            insecure_no_auth = os.environ.get("AIRUNNER_INSECURE_NO_AUTH", "0") == "1"
            if not is_loopback_host(self.host) and not insecure_no_auth and not api_key:
                logger.error(
                    "Refusing to bind to non-loopback host without AIRUNNER_API_KEY. "
                    "Set AIRUNNER_API_KEY or AIRUNNER_INSECURE_NO_AUTH=1 (not recommended)."
                )
                return

            app = create_app(app_instance=self.app_instance)

            logger.info(f"FastAPI server listening on http://{self.host}:{self.port}")
            logger.info("Available endpoints: /health, /llm/*, /art, /api/v1/*")

            config = uvicorn.Config(
                app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=access_logs_enabled(),
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
