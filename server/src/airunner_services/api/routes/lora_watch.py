"""LoRA file-system change notifications via WsEventBus.

Starts a background ``watchdog`` observer that monitors all
``{AIRUNNER_BASE_PATH}/art/models/**/lora/`` directories for
``.safetensors`` file changes (created, modified, deleted, moved).
Each detected change pushes a ``reload`` event via ``WsEventBus``.
"""

from __future__ import annotations

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

_LORA_GLOB = "**/lora/"
_SAFETENSORS_SUFFIX = ".safetensors"


def _discover_lora_dirs() -> list[Path]:
    """Return every ``lora`` directory under the art models tree."""
    art_models = Path(AIRUNNER_BASE_PATH) / "art" / "models"
    if not art_models.is_dir():
        return []
    return [p for p in art_models.glob(_LORA_GLOB) if p.is_dir()]


class _LoraFileHandler(FileSystemEventHandler):
    """Emits a reload event when a ``.safetensors`` file changes."""

    def _on_any_event(self, event):
        src = getattr(event, "src_path", "") or ""
        if not src.lower().endswith(_SAFETENSORS_SUFFIX):
            return
        if event.is_directory:
            return
        logger.debug("LoRA watch event: %s %s", event.event_type, src)
        _notify_subscribers()

    def on_created(self, event):
        """Called when a file or directory is created."""
        self._on_any_event(event)

    def on_modified(self, event):
        """Called when a file or directory is modified."""
        self._on_any_event(event)

    def on_deleted(self, event):
        """Called when a file or directory is deleted."""
        self._on_any_event(event)

    def on_moved(self, event):
        """Called when a file or directory is moved."""
        src = getattr(event, "src_path", "") or ""
        dest = getattr(event, "dest_path", "") or ""
        if src.lower().endswith(_SAFETENSORS_SUFFIX) or (
            dest.lower().endswith(_SAFETENSORS_SUFFIX)
        ):
            logger.debug("LoRA watch move event: %s -> %s", src, dest)
            _notify_subscribers()


def _notify_subscribers() -> None:
    """Push a ``reload`` event via WsEventBus."""
    WsEventBus().broadcast("loras", {"type": "reload"})


def _start_watcher() -> None:
    """Start the background ``watchdog`` observer (idempotent)."""
    global _watcher_started, _watcher_observer
    if _watcher_started:
        return
    _watcher_started = True

    dirs = _discover_lora_dirs()
    if not dirs:
        logger.info(
            "No LoRA directories found under %s/art/models — "
            "watcher will not monitor anything until directories appear.",
            AIRUNNER_BASE_PATH,
        )
        return

    handler = _LoraFileHandler()
    observer = _Observer()
    for d in dirs:
        logger.debug("Watching LoRA directory: %s", d)
        observer.schedule(handler, str(d), recursive=True)

    observer.daemon = True
    observer.start()
    _watcher_observer = observer
    logger.info(
        "LoRA file watcher started — monitoring %d director%s",
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
