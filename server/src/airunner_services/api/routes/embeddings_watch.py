"""SSE endpoint for embedding file-system change notifications.

Starts a background ``watchdog`` observer that monitors
``{AIRUNNER_BASE_PATH}/art/models/embeddings/`` and
``{AIRUNNER_BASE_PATH}/text/models/llm/embedding/`` directories for
embedding file changes (created, modified, deleted, moved).
Each detected change pushes a ``data: {"type": "reload"}\n\n`` event
to every connected SSE client.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer as _Observer

from airunner_services.settings import AIRUNNER_BASE_PATH

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Module-level watcher state ──────────────────────────────────────────
_watch_subscribers: list[queue.Queue[bytes]] = []
_watch_lock = threading.Lock()
_watcher_started = False
_watcher_observer: _Observer | None = None

EMBEDDING_EXTENSIONS = frozenset({".pt", ".safetensors", ".bin", ".pth"})


def _discover_embedding_dirs() -> list[Path]:
    """Return every ``embeddings`` directory under the models tree.

    Scans version-specific subdirectories (e.g.
    ``art/models/SDXL 1.0/embeddings/``) via ``**/embeddings/`` glob,
    plus the legacy flat path and the LLM embedding directory.
    """
    art_models = Path(AIRUNNER_BASE_PATH) / "art" / "models"
    candidates: list[Path] = [
        Path(AIRUNNER_BASE_PATH) / "text" / "models" / "llm" / "embedding",
    ]
    if art_models.is_dir():
        candidates.extend(
            p for p in art_models.glob("**/embeddings/") if p.is_dir()
        )
    return [p for p in candidates if p.is_dir()]


class _EmbeddingFileHandler(FileSystemEventHandler):
    """Emits a reload event when an embedding file changes."""

    def _on_any_event(self, event):
        src = getattr(event, "src_path", "") or ""
        if not src.lower().endswith(tuple(EMBEDDING_EXTENSIONS)):
            return
        if event.is_directory:
            return
        logger.debug("Embedding watch event: %s %s", event.event_type, src)
        _notify_subscribers()

    def on_created(self, event):
        self._on_any_event(event)

    def on_modified(self, event):
        self._on_any_event(event)

    def on_deleted(self, event):
        self._on_any_event(event)

    def on_moved(self, event):
        src = getattr(event, "src_path", "") or ""
        dest = getattr(event, "dest_path", "") or ""
        if src.lower().endswith(tuple(EMBEDDING_EXTENSIONS)) or (
            dest.lower().endswith(tuple(EMBEDDING_EXTENSIONS))
        ):
            logger.debug(
                "Embedding watch move event: %s -> %s", src, dest,
            )
            _notify_subscribers()


def _notify_subscribers() -> None:
    """Push a ``reload`` event to every connected SSE subscriber."""
    payload = json.dumps({"type": "reload"}).encode("utf-8") + b"\n"
    line = b"data: " + payload + b"\n"
    with _watch_lock:
        dead: list[queue.Queue[bytes]] = []
        for q in _watch_subscribers:
            try:
                q.put_nowait(line)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _watch_subscribers.remove(q)


def _start_watcher() -> None:
    """Start the background ``watchdog`` observer (idempotent)."""
    global _watcher_started, _watcher_observer
    if _watcher_started:
        return
    _watcher_started = True

    dirs = _discover_embedding_dirs()
    if not dirs:
        logger.info(
            "No embedding directories found under %s — "
            "watcher will not monitor anything until directories appear.",
            AIRUNNER_BASE_PATH,
        )
        return

    handler = _EmbeddingFileHandler()
    observer = _Observer()
    for d in dirs:
        logger.debug("Watching embedding directory: %s", d)
        observer.schedule(handler, str(d), recursive=True)

    observer.daemon = True
    observer.start()
    _watcher_observer = observer
    logger.info(
        "Embedding file watcher started — "
        "monitoring %d director%s",
        len(dirs),
        "ies" if len(dirs) != 1 else "y",
    )


def _stop_watcher() -> None:
    """Stop the background watchdog observer."""
    global _watcher_observer, _watcher_started
    obs = _watcher_observer
    if obs is not None:
        obs.stop()
        obs.join(timeout=2)
        _watcher_observer = None
    _watcher_started = False


# ── SSE endpoint ────────────────────────────────────────────────────────


@router.get("/embeddings/watch")
def watch_embeddings() -> StreamingResponse:
    """SSE stream that emits ``data: {"type": "reload"}\n\n``

    whenever an embedding file (``.pt``, ``.safetensors``, ``.bin``,
    ``.pth``) is created, modified, or deleted inside either the
    ``art/models/embeddings/`` or ``text/models/llm/embedding/``
    directory.
    """
    _start_watcher()

    q: queue.Queue[bytes] = queue.Queue(maxsize=128)

    with _watch_lock:
        _watch_subscribers.append(q)

    def _cleanup():
        with _watch_lock:
            if q in _watch_subscribers:
                _watch_subscribers.remove(q)

    def event_stream():  # noqa: DOC502
        try:
            while True:
                try:
                    data = q.get(timeout=30)
                    yield data
                except queue.Empty:
                    yield b": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            _cleanup()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
