"""Knowledge-base document file-system change notifications via WsEventBus.

Starts a background ``watchdog`` observer that monitors configured
knowledge-base document directories for supported document file changes
(created, modified, deleted, moved).
Each detected change pushes a ``reload`` event via ``WsEventBus``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer as _Observer

from airunner_services.api.routes.events import WsEventBus
from airunner_services.settings import AIRUNNER_BASE_PATH

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Module-level watcher state ──────────────────────────────────────────
_watcher_started = False
_watcher_observer: _Observer | None = None

# Document extensions supported by the knowledge base.
DOCUMENT_EXTENSIONS = frozenset({
    ".mobi", ".pdf", ".epub", ".html", ".htm",
    ".md", ".txt", ".zim", ".doc", ".docx", ".odt",
})


def _discover_kb_dirs() -> list[Path]:
    """Return knowledge-base directories to watch.

    Watches the default document, ebook, and webpage directories
    configured through path settings, plus a ``knowledge_base``
    subdirectory under the base path.
    """
    candidates = [
        Path(AIRUNNER_BASE_PATH) / "text" / "other" / "documents",
        Path(AIRUNNER_BASE_PATH) / "text" / "other" / "ebooks",
        Path(AIRUNNER_BASE_PATH) / "text" / "other" / "webpages",
        Path(AIRUNNER_BASE_PATH) / "knowledge_base",
    ]
    return [p for p in candidates if p.is_dir()]


class _KBDocumentHandler(FileSystemEventHandler):
    """Emits a reload event when a supported document file changes."""

    def _on_any_event(self, event):
        src = getattr(event, "src_path", "") or ""
        if not src.lower().endswith(tuple(DOCUMENT_EXTENSIONS)):
            return
        if event.is_directory:
            return
        logger.debug("KB watch event: %s %s", event.event_type, src)
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
        if src.lower().endswith(tuple(DOCUMENT_EXTENSIONS)) or (
            dest.lower().endswith(tuple(DOCUMENT_EXTENSIONS))
        ):
            logger.debug(
                "KB watch move event: %s -> %s", src, dest,
            )
            _notify_subscribers()


def _notify_subscribers() -> None:
    """Push a ``reload`` event via WsEventBus."""
    WsEventBus().broadcast("documents", {"type": "reload"})


def _start_watcher() -> None:
    """Start the background ``watchdog`` observer (idempotent)."""
    global _watcher_started, _watcher_observer
    if _watcher_started:
        return
    _watcher_started = True

    dirs = _discover_kb_dirs()
    if not dirs:
        logger.info(
            "No knowledge-base directories found under %s — "
            "watcher will not monitor anything until directories appear.",
            AIRUNNER_BASE_PATH,
        )
        return

    handler = _KBDocumentHandler()
    observer = _Observer()
    for d in dirs:
        logger.debug("Watching KB directory: %s", d)
        observer.schedule(handler, str(d), recursive=True)

    observer.daemon = True
    observer.start()
    _watcher_observer = observer
    logger.info(
        "KB file watcher started — "
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
