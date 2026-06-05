"""Admin handler mixin for legacy API handlers (memory, DB, shutdown)."""

import os
import threading
import time

from airunner_services.settings import AIRUNNER_LOG_LEVEL
from airunner_services.utils.application.get_logger import get_logger


class AdminHandlersMixin:
    """Mixin providing admin handlers for BaseHTTPRequestHandler."""

    def _handle_reset_memory(self):
        """Reset the LLM conversation memory."""
        logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        logger.info("Resetting LLM memory...")
        from airunner_services.api.legacy_server import get_api

        api = get_api()
        if api is not None:
            from airunner_services.contract_enums import SignalCode

            mediator = getattr(api, "signal_mediator", None)
            if mediator is not None:
                mediator.emit_signal(
                    SignalCode.MEMORY_RESET_AND_LOAD_SIGNAL,
                    {},
                )
                logger.info("Memory reset signal emitted")
        self._send_json_response(
            {"status": "ok", "message": "Memory reset initiated"},
        )

    def _handle_reset_database(self):
        """Reset the application database."""
        logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        logger.info("Resetting database...")
        try:
            from airunner_services.database.session import session_scope
            from airunner_services.database.models.conversation import (
                Conversation,
            )

            with session_scope() as session:
                session.query(Conversation).delete()
                session.commit()
            logger.info("Database reset complete")
            self._send_json_response(
                {"status": "ok", "message": "Database reset completed"},
            )
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            self._send_json_response(
                {"status": "error", "message": str(e)},
                status=500,
            )

    def _handle_shutdown(self):
        """Gracefully shut down the server."""
        logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        logger.info("Shutdown requested via admin endpoint")

        def delayed_shutdown():
            time.sleep(0.5)
            os._exit(0)

        self._send_json_response(
            {"status": "ok", "message": "Server shutting down..."},
        )
        threading.Thread(target=delayed_shutdown, daemon=True).start()
