"""REST and SSE endpoints for browsing generated images by date.

Provides directory-based browsing of images stored under
``{AIRUNNER_BASE_PATH}/art/other/images/`` organised by ``YYYYMMDD``
subdirectories, lazy-loaded thumbnail generation with PNG caching,
and a ``watchdog``-based SSE endpoint for file-system change
notifications.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from airunner_services.api.routes.events import WsEventBus
from PIL import Image
from pydantic import BaseModel
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer as _Observer

from airunner_services.settings import AIRUNNER_BASE_PATH

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Path helpers ──────────────────────────────────────────────────────────

_IMAGES_ROOT = Path(AIRUNNER_BASE_PATH) / "art" / "other" / "images"
_CACHE_ROOT = Path(AIRUNNER_BASE_PATH) / "cache" / "thumbs"

_THUMB_MAX_SIZE = (200, 200)
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

# Allowed root directories for path-safety checks.
_SAFE_ROOTS = (_IMAGES_ROOT.resolve(), _CACHE_ROOT.resolve())


def _validate_path_safe(
    candidate: Path,
    *,
    label: str = "Path",
) -> Path:
    """Resolve and verify that *candidate* sits inside one of the allowed
    root directories.  Raises ``HTTPException(403)`` on mismatch."""
    # Reject path traversal components before resolving.
    if ".." in candidate.parts:
        raise HTTPException(
            status_code=403,
            detail=f"{label} must not contain path traversal elements",
        )
    resolved = candidate.resolve()
    safe = False
    for root in _SAFE_ROOTS:
        try:
            resolved.relative_to(root)
            safe = True
            break
        except ValueError:
            continue
    if not safe:
        raise HTTPException(
            status_code=403,
            detail=f"{label} resolves outside the expected directory",
        )
    return resolved


def _validate_date_component(date_str: str) -> str:
    """Validate that *date_str* contains exactly 8 digits (``YYYYMMDD``)."""
    if not date_str.isdigit() or len(date_str) != 8:
        raise HTTPException(
            status_code=422,
            detail="Date must be in YYYYMMDD format",
        )
    return date_str


def _validate_filename_component(filename: str) -> str:
    """Reject filenames that contain path separators, null bytes, or
    attempt directory traversal."""
    if not filename or "\x00" in filename:
        raise HTTPException(status_code=422, detail="Invalid filename")
    # Reject anything with a path separator
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=422, detail="Filename must not contain path separators")
    # Reject traversal components
    if filename in (".", ".."):
        raise HTTPException(status_code=422, detail="Invalid filename")
    return filename


def _date_dir(date_str: str) -> Path:
    """Return the ``YYYYMMDD`` directory path for a given date string."""
    return _IMAGES_ROOT / date_str


def _cache_path(date_str: str, filename: str) -> Path:
    """Return the cached thumbnail path for one image."""
    thumb_dir = _CACHE_ROOT / date_str
    thumb_dir.mkdir(parents=True, exist_ok=True)
    return thumb_dir / f"{filename}.png"


def _list_image_files(directory: Path) -> list[Path]:
    """Return sorted image file paths in one date directory."""
    if not directory.is_dir():
        return []
    return sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in _IMAGE_EXTENSIONS
    )


def _format_label(date_str: str) -> str:
    """Convert ``YYYYMMDD`` to ``YYYY-MM-DD``."""
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def _extract_metadata(path: Path) -> dict | None:
    """Extract PNG tEXt metadata chunks from an image file.

    Uses PIL/Pillow's ``img.info`` which exposes PNG metadata such
    as ``parameters`` (automatic1111/webui format), ``prompt``,
    ``negative_prompt``, ``seed``, etc.
    """
    try:
        if path.suffix.lower() != ".png":
            return None
        with Image.open(path) as img:
            info: dict = img.info or {}
            # Filter string values only
            metadata: dict = {
                k: v for k, v in info.items()
                if isinstance(v, str)
            }
            # Try to parse the common "parameters" JSON/metadata blob
            raw = metadata.get("parameters") or metadata.get("params")
            if raw and isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        metadata["parameters"] = parsed
                    else:
                        metadata["parameters_text"] = str(raw)
                except (json.JSONDecodeError, TypeError):
                    metadata["parameters_text"] = str(raw)
            return metadata or None
    except Exception as exc:
        logger.debug("Could not extract metadata from %s: %s", path, exc)
        return None


# ── File watcher state ─────────────────────────────────────────────────

_WATCH_DIR = _IMAGES_ROOT
_watcher_started = False
_watcher_observer = None  # type: ignore[valid-type]


class _ImageFileHandler(FileSystemEventHandler):
    """Emits a reload event when an image file or directory changes."""

    def _on_any_event(self, event):
        if event.is_directory:
            _notify_subscribers()
            return
        src = getattr(event, "src_path", "") or ""
        if src.lower().endswith(tuple(_IMAGE_EXTENSIONS)):
            logger.debug("Image watch event: %s %s", event.event_type, src)
            _notify_subscribers()

    def on_created(self, event):
        self._on_any_event(event)

    def on_modified(self, event):
        self._on_any_event(event)

    def on_deleted(self, event):
        self._on_any_event(event)

    def on_moved(self, event):
        self._on_any_event(event)


def _notify_subscribers() -> None:
    """Push a ``reload`` event via WsEventBus."""
    WsEventBus().broadcast("images", {"type": "reload"})


def _start_watcher() -> None:
    """Start the background ``watchdog`` observer (idempotent)."""
    global _watcher_started, _watcher_observer
    if _watcher_started:
        return
    _watcher_started = True

    if not _WATCH_DIR.is_dir():
        logger.info("Image directory %s does not exist yet", _WATCH_DIR)
        return

    handler = _ImageFileHandler()
    observer = _Observer()
    observer.schedule(handler, str(_WATCH_DIR), recursive=True)
    observer.daemon = True
    observer.start()
    _watcher_observer = observer
    logger.info("Image file watcher started — monitoring %s", _WATCH_DIR)


def _stop_watcher() -> None:
    """Stop the background watchdog observer."""
    global _watcher_observer, _watcher_started
    obs = _watcher_observer
    if obs is not None:
        obs.stop()  # type: ignore[union-attr]
        obs.join(timeout=2)  # type: ignore[union-attr]
        _watcher_observer = None
    _watcher_started = False


# SSE endpoint removed — events now broadcast via WsEventBus.
# The file watcher above still triggers _notify_subscribers which
# calls WsEventBus().broadcast("images", {"type": "reload"}).


# ── Date listing ──────────────────────────────────────────────────────────


@router.get("/images/dates")
def list_dates():
    """List all ``YYYYMMDD`` subdirectories under the images root."""
    if not _IMAGES_ROOT.is_dir():
        return {"dates": []}

    dates: list[str] = sorted(
        [entry.name for entry in _IMAGES_ROOT.iterdir()
         if entry.is_dir() and entry.name.isdigit() and len(entry.name) == 8],
        reverse=True,
    )
    return {
        "dates": [
            {"value": d, "label": _format_label(d)} for d in dates
        ],
    }


# ── Image listing (paginated) ─────────────────────────────────────────────


@router.get("/images/{date}")
def list_images(
    date: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """List image files in a ``YYYYMMDD`` directory with pagination."""
    _validate_date_component(date)
    directory = _date_dir(date)
    _validate_path_safe(directory, label="Date directory")
    if not directory.is_dir():
        raise HTTPException(status_code=404, detail="Date directory not found")

    all_files = _list_image_files(directory)
    total = len(all_files)
    page = all_files[offset: offset + limit]

    images = []
    for p in page:
        meta = _extract_metadata(p) if p.suffix.lower() == ".png" else None
        try:
            stat = p.stat()
            file_size = stat.st_size
            file_timestamp = stat.st_mtime
        except OSError:
            file_size = 0
            file_timestamp = 0.0
        images.append({
            "id": p.name,
            "image_url": (
                f"/api/v1/art/images/{date}/full/{p.name}"
            ),
            "thumbnail_url": (
                f"/api/v1/art/images/{date}/thumb/{p.name}"
            ),
            "file_path": str(p),
            "file_size": file_size,
            "file_timestamp": file_timestamp,
            "metadata": meta,
        })

    return {
        "total": total,
        "images": images,
    }


# ── Single image info ─────────────────────────────────────────────────────


@router.get("/images/{date}/info/{filename}")
def get_image_info(date: str, filename: str):
    """Return file info and metadata for one image file."""
    _validate_date_component(date)
    _validate_filename_component(filename)
    source = _date_dir(date) / filename
    _validate_path_safe(source, label="Image file")
    if not source.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    meta = _extract_metadata(source) if source.suffix.lower() == ".png" else None
    try:
        file_size = source.stat().st_size
    except OSError:
        file_size = 0

    return {
        "id": source.name,
        "file_path": str(source),
        "file_size": file_size,
        "metadata": meta,
        "image_url": (
            f"/api/v1/art/images/{date}/full/{source.name}"
        ),
        "thumbnail_url": (
            f"/api/v1/art/images/{date}/thumb/{source.name}"
        ),
    }


# ── Full image serving ────────────────────────────────────────────────────


@router.get("/images/{date}/full/{filename}")
def serve_full_image(date: str, filename: str):
    """Serve the original full-size image file."""
    _validate_date_component(date)
    _validate_filename_component(filename)
    source = _date_dir(date) / filename
    _validate_path_safe(source, label="Image file")
    if not source.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    media_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_map.get(source.suffix.lower(), "image/png")
    return FileResponse(str(source), media_type=media_type)


# ── Thumbnail serving ─────────────────────────────────────────────────────


@router.get("/images/{date}/thumb/{filename}")
def serve_thumbnail(date: str, filename: str):
    """Serve a resized thumbnail (max 200x200) of the requested image."""
    _validate_date_component(date)
    _validate_filename_component(filename)
    source = _date_dir(date) / filename
    _validate_path_safe(source, label="Image file")
    if not source.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    cached = _cache_path(date, filename)
    _validate_path_safe(cached, label="Thumbnail cache")

    try:
        img = Image.open(source)
        img.thumbnail(_THUMB_MAX_SIZE)
        img.save(str(cached), format="PNG")
        return FileResponse(str(cached), media_type="image/png")
    except Exception as exc:
        logger.error("Failed to generate thumbnail for %s: %s", source, exc)
        raise HTTPException(status_code=500, detail="Thumbnail generation failed") from exc


# ── Delete image ─────────────────────────────────────────────────────────


class _DeleteResponse(BaseModel):
    success: bool
    deleted: str


@router.delete("/images/{date}/delete/{filename}")
def delete_image(date: str, filename: str) -> _DeleteResponse:
    """Delete an image file from disk."""
    _validate_date_component(date)
    _validate_filename_component(filename)
    source = _date_dir(date) / filename
    _validate_path_safe(source, label="Image file")
    if not source.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    source.unlink()
    # Also delete cached thumbnail
    cached = _cache_path(date, filename)
    _validate_path_safe(cached, label="Thumbnail cache")
    return _DeleteResponse(success=True, deleted=filename)


# ── Rename image ─────────────────────────────────────────────────────────


class _RenameImageRequest(BaseModel):
    new_filename: str


class _RenameResponse(BaseModel):
    success: bool
    new_id: str


@router.put("/images/{date}/rename/{filename}")
def rename_image(
    date: str,
    filename: str,
    body: _RenameImageRequest,
) -> _RenameResponse:
    """Rename an image file on disk, appending a number if the new name
    exists."""
    _validate_date_component(date)
    _validate_filename_component(filename)
    _validate_filename_component(body.new_filename)
    source = _date_dir(date) / filename
    _validate_path_safe(source, label="Image file")
    if not source.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    new_name = body.new_filename
    orig_ext = source.suffix
    user_ext = Path(new_name).suffix
    if user_ext and user_ext.lower() != orig_ext.lower():
        # User provided a different extension — keep user's name
        # and append the real extension
        new_name = new_name + orig_ext
    elif not user_ext:
        # No extension provided — append the original
        new_name = new_name + orig_ext
    # else: user provided correct extension — keep as-is

    dest = _date_dir(date) / new_name
    _validate_path_safe(dest, label="Destination file")
    # Handle name collisions
    if dest.is_file():
        stem = dest.stem
        suffix = dest.suffix
        counter = 1
        while dest.is_file():
            dest = _date_dir(date) / f"{stem} ({counter}){suffix}"
            counter += 1

    source.rename(dest)

    # Also rename cached thumbnail
    old_cached = _cache_path(date, filename)
    if old_cached.is_file():
        new_cached = _cache_path(date, dest.name)
        old_cached.rename(new_cached)

    return _RenameResponse(success=True, new_id=dest.name)
