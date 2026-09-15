"""Shared helpers for legacy compatibility routes."""

import os
import signal
import threading

from fastapi import HTTPException, Request


def get_airunner_app(req: Request):
    """Return the AIRunner app or raise when it is unavailable."""
    app = getattr(req.app.state, "airunner_app", None)
    if app is None:
        raise HTTPException(status_code=503, detail="AI Runner app not available")
    return app


def queue_service_llm_unload(req: Request) -> bool:
    """Queue one LLM unload through the lifecycle service when possible."""
    lifecycle_service = getattr(req.app.state, "lifecycle_service", None)
    queue_unload = getattr(lifecycle_service, "queue_llm_unload", None)
    if not callable(queue_unload):
        return False
    return bool(queue_unload(source="daemon_admin_unload"))


def terminate_current_process() -> None:
    """Send SIGTERM to the current process for graceful daemon shutdown."""
    os.kill(os.getpid(), signal.SIGTERM)


def schedule_process_shutdown(delay_seconds: float = 0.1) -> None:
    """Terminate the current process after the HTTP response is returned."""
    timer = threading.Timer(delay_seconds, terminate_current_process)
    timer.daemon = True
    timer.start()