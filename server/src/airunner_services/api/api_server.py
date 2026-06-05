"""Wrapper for running the FastAPI application as a standalone server."""

from __future__ import annotations

from typing import Optional

import uvicorn

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application import get_logger

from .server import access_logs_enabled, create_app

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class APIServer:
    """FastAPI server wrapper for AI Runner."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8188,
        app_instance=None,
        allowed_origins: Optional[list] = None,
        enable_cors: bool = True,
    ):
        """
        Initialize API server.

        Args:
            host: Host to bind to
            port: Port to listen on
            app_instance: Optional App instance for accessing
                AI Runner internals
            allowed_origins: List of allowed CORS origins
            enable_cors: Whether to enable CORS
        """
        self.host = host
        self.port = port
        self.app_instance = app_instance
        self.app = create_app(
            allowed_origins, enable_cors, app_instance=app_instance
        )
        self.server = None

    def start(self):
        """Start the API server (blocking call)."""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=access_logs_enabled(),
        )
        self.server = uvicorn.Server(config)
        logger.info(
            "Starting API server on %s:%s",
            self.host,
            self.port,
        )
        self.server.run()

    def stop(self):
        """Stop the API server."""
        if self.server:
            logger.info("Stopping API server...")
            self.server.should_exit = True
            self.server = None
