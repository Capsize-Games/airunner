"""API Server Thread for headless mode.

Runs the headless HTTP API inside uvicorn/FastAPI.

We keep the legacy endpoints (/llm/*, /art, etc.) via a compatibility router
so existing clients continue to work.
"""

import threading

import os

import uvicorn
from PySide6.QtCore import QCoreApplication

from airunner.api.server import (
    access_logs_enabled,
    create_app,
    is_loopback_host,
)
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
        host: Host address to bind to (default: localhost)
        port: Port to listen on (default: 8080)
    """

    def __init__(
        self,
        app_instance=None,
        host: str = AIRUNNER_HEADLESS_SERVER_HOST,
        port: int = AIRUNNER_HEADLESS_SERVER_PORT,
    ):
        super().__init__(daemon=True)
        self.app_instance = app_instance
        self.host = host
        self.port = port
        self.server: uvicorn.Server | None = None
        self._stop_event = threading.Event()

    def _resolve_app_instance(self):
        """Return the app instance bound to the FastAPI server thread."""
        if self.app_instance is not None:
            return self.app_instance
        app = QCoreApplication.instance()
        if app is None:
            return None
        return getattr(app, "api", None)

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

            api = self._resolve_app_instance()
            if api is None:
                logger.error("Cannot start API server without an app instance")
                return
            app = create_app(app_instance=api)

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
