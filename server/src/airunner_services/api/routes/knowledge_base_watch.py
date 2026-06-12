"""Knowledge-base document file-system change notifications via WsEventBus.

Scans document directories on startup to populate the Document database
table, then starts a background ``watchdog`` observer that monitors for
file changes (created, modified, deleted, moved).
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

# Document extensions supported by the knowledge base.
DOCUMENT_EXTENSIONS = frozenset(
    {
        ".mobi",
        ".pdf",
        ".epub",
        ".html",
        ".htm",
        ".md",
        ".txt",
        ".zim",
        ".doc",
        ".docx",
        ".odt",
    }
)


def _discover_kb_dirs() -> list[Path]:
    """Return knowledge-base directories to watch."""
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
                "KB watch move event: %s -> %s",
                src,
                dest,
            )
            _notify_subscribers()


def _notify_subscribers() -> None:
    """Push a ``reload`` event via WsEventBus."""
    WsEventBus().broadcast("documents", {"type": "reload"})


def _collect_disk_files(dirs: list[Path]) -> set[Path]:
    """Collect all supported document files from disk directories."""
    disk_files: set[Path] = set()
    for d in dirs:
        for ext in DOCUMENT_EXTENSIONS:
            for p in d.rglob(f"*{ext}"):
                if p.is_file():
                    disk_files.add(p.resolve())
    return disk_files


def _collect_existing_paths(session) -> tuple[set[str], set[str]]:
    """Collect disk and database file paths."""
    from airunner_services.database.models.document import Document

    existing = {
        Path(str(d.path)).resolve()
        for d in session.query(Document).all()
        if d.path
    }
    disk_paths = {str(p) for p in _collect_disk_files(_discover_kb_dirs())}
    existing_paths = {str(p) for p in existing}
    return disk_paths, existing_paths


def _add_new_documents(session, new_paths: set[str]) -> None:
    """Add new document records to the database."""
    from airunner_services.database.models.document import Document

    for path_str in sorted(new_paths):
        session.add(Document(path=path_str, active=False, indexed=False))


def _remove_stale_documents(session, stale_paths: set[str]) -> None:
    """Remove stale document records from the database."""
    from airunner_services.database.models.document import Document

    if stale_paths:
        session.query(Document).filter(
            Document.path.in_(list(stale_paths))
        ).delete(synchronize_session="fetch")


def sync_documents(session) -> None:
    """Sync the Document table for the CURRENT tenant with files on disk.

    Runs inside the caller's (tenant-scoped) ``session`` so documents are
    registered into the right schema — this is what makes the knowledge
    base panel reflect the on-disk folder per account. Previously the only
    sync ran in a tenant-less startup thread, which registered everything
    into ``tenant_anonymous`` where no authenticated client could see it.

    No-op when filesystem ingestion is disabled (the production storage
    extension switches to upload-only / S3). The caller owns the
    transaction; this flushes but does not commit.
    """
    from airunner_services.storage import filesystem_ingestion_enabled

    if not filesystem_ingestion_enabled():
        return

    dirs = _discover_kb_dirs()
    if not dirs:
        return

    disk_paths, existing_paths = _collect_existing_paths(session)
    new_paths = disk_paths - existing_paths
    stale_paths = existing_paths - disk_paths

    _add_new_documents(session, new_paths)
    _remove_stale_documents(session, stale_paths)

    if new_paths or stale_paths:
        session.flush()
        logger.info(
            "KB sync (tenant): added %d, removed %d document(s)",
            len(new_paths),
            len(stale_paths),
        )


def _setup_observer(dirs: list[Path]) -> _Observer:
    """Create and start a watchdog observer for the given directories."""
    handler = _KBDocumentHandler()
    observer = _Observer()
    for d in dirs:
        logger.debug("Watching KB directory: %s", d)
        observer.schedule(handler, str(d), recursive=True)
    observer.daemon = True
    observer.start()
    return observer


def _start_watcher() -> None:
    """Start the background ``watchdog`` observer (idempotent).

    Disabled entirely when filesystem ingestion is off (production storage
    extension / object storage). The startup folder→DB scan was removed:
    syncing now happens per-request in the tenant's schema (see
    :func:`sync_documents`) instead of in this tenant-less thread, which
    used to register every document into ``tenant_anonymous``.
    """
    from airunner_services.storage import filesystem_ingestion_enabled

    global _watcher_started, _watcher_observer
    if _watcher_started:
        return
    if not filesystem_ingestion_enabled():
        logger.info("Filesystem ingestion disabled — KB watcher not started.")
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
    _watcher_observer = _setup_observer(dirs)
    logger.info(
        "KB file watcher started — monitoring %d director%s",
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
