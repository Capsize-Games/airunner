"""
API Server Thread for headless mode.

Runs an HTTP server with /health, /llm, /art, /stt, /tts endpoints
without requiring Qt GUI components.
"""

import threading
from http.server import HTTPServer
from socketserver import ThreadingMixIn
from airunner.components.server.api.server import AIRunnerAPIRequestHandler
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.settings import (
    AIRUNNER_HEADLESS_SERVER_HOST,
    AIRUNNER_HEADLESS_SERVER_PORT,
)

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

    daemon_threads = True
    allow_reuse_address = True


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
        self.server = None
        self._stop_event = threading.Event()

    def run(self):
        """Start the HTTP server and serve requests."""
        try:
            self.server = ThreadedHTTPServer(
                (self.host, self.port), AIRunnerAPIRequestHandler
            )
            logger.info(
                f"API server listening on http://{self.host}:{self.port}"
            )
            logger.info("Available endpoints: /health, /llm, /art, /stt, /tts")

            # Serve requests until stopped
            while not self._stop_event.is_set():
                self.server.handle_request()

        except Exception as e:
            logger.error(f"API server error: {e}", exc_info=True)
        finally:
            if self.server:
                self.server.server_close()

    def stop(self):
        """Stop the server gracefully."""
        logger.info("Stopping API server...")
        self._stop_event.set()
        if self.server:
            self.server.shutdown()
