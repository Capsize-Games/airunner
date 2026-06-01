"""Thumbnail model for the batch gallery.

This module provides a Qt list model that supports lazy loading of image
thumbnails backed by an optional on-disk cache. The model is designed to power
virtualised views such as :class:`~PySide6.QtWidgets.QListView` in icon mode so
that the gallery remains responsive even when a directory contains thousands of
images.
"""

from __future__ import annotations

import hashlib
import io
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from PIL import Image
from PySide6.QtCore import (
    QAbstractListModel,
    QMimeData,
    QModelIndex,
    QObject,
    Qt,
    QSize,
    QRunnable,
    QThreadPool,
    Signal,
    QUrl,
)
from PySide6.QtGui import QIcon, QImage, QPixmap, QBrush, QColor


@dataclass(slots=True)
class GalleryEntry:
    """Represents a single visible item in the batch gallery."""

    path: Optional[str]
    display: str
    is_batch: bool
    batch_folder: Optional[str] = None
    total: Optional[int] = None
    tooltip: Optional[str] = None


class _ThumbnailSignals(QObject):
    """Signals emitted by background thumbnail jobs."""

    finished = Signal(str, object, float)


class _ThumbnailJob(QRunnable):
    """Background worker that produces PNG thumbnail bytes for an image file."""

    def __init__(self, filepath: str, size: int, cache_dir: Optional[Path]):
        super().__init__()
        self.filepath = filepath
        self.size = size
        self.cache_dir = cache_dir
        self.signals = _ThumbnailSignals()

    def run(self) -> None:  # pragma: no cover - Qt thread
        mtime = 0.0
        png_bytes = None

        try:
            if not os.path.exists(self.filepath):
                self.signals.finished.emit(self.filepath, None, 0.0)
                return

            mtime = float(os.path.getmtime(self.filepath))
            cache_path = self._cache_path(self.filepath, mtime)

            if cache_path is not None and cache_path.exists():
                try:
                    png_bytes = cache_path.read_bytes()
                except IOError:
                    png_bytes = None

            if png_bytes is None:
                png_bytes = self._create_thumbnail(self.filepath, self.size)
                if cache_path is not None and png_bytes is not None:
                    try:
                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        cache_path.write_bytes(png_bytes)
                    except IOError:
                        pass
        except Exception:
            png_bytes = None
            mtime = 0.0

        self.signals.finished.emit(self.filepath, png_bytes, mtime)

    def _cache_path(self, filepath: str, mtime: float) -> Optional[Path]:
        if self.cache_dir is None:
            return None
        digest_source = f"{filepath}:{mtime}".encode("utf-8")
        digest = hashlib.sha1(digest_source).hexdigest()
        return self.cache_dir / f"{digest}.png"

    @staticmethod
    def _create_thumbnail(filepath: str, size: int) -> Optional[bytes]:
        try:
            with Image.open(filepath) as handle:
                handle.thumbnail((size, size), Image.Resampling.LANCZOS)
                if handle.mode != "RGBA":
                    handle = handle.convert("RGBA")
                buffer = io.BytesIO()
                handle.save(buffer, format="PNG")
                return buffer.getvalue()
        except Exception:
            return None


class ThreadSafeLRUCache:
    """Small thread-safe LRU cache for :class:`~PySide6.QtGui.QPixmap` values."""

    def __init__(self, max_items: int = 512):
        self.max_items = max_items
        self._lock = threading.Lock()
        self._order: List[str] = []
        self._data: dict[str, QPixmap] = {}

    def get(self, key: str) -> Optional[QPixmap]:
        with self._lock:
            pixmap = self._data.get(key)
            if pixmap is None:
                return None
            try:
                self._order.remove(key)
            except ValueError:
                pass
            self._order.insert(0, key)
            return pixmap

    def put(self, key: str, value: QPixmap) -> None:
        with self._lock:
            if key in self._data:
                try:
                    self._order.remove(key)
                except ValueError:
                    pass
            self._data[key] = value
            self._order.insert(0, key)
            while len(self._order) > self.max_items:
                tail = self._order.pop()
                self._data.pop(tail, None)

    def clear(self) -> None:
        with self._lock:
            self._order.clear()
            self._data.clear()


class ThumbnailListModel(QAbstractListModel):
    """Model supplying lazily loaded thumbnails for the gallery view."""

    def __init__(
        self,
        entries: Optional[Sequence[GalleryEntry]] = None,
        thumb_size: int = 256,
        cache_dir: Optional[str] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)

        # set background to transparent (stored as QColor)
        self._background_color: Optional[QColor] = None
        self.set_background_color(Qt.transparent)

        self._entries: List[GalleryEntry] = list(entries or [])
        self.thumb_size = thumb_size
        self._placeholder = self._make_placeholder()
        self._cache = ThreadSafeLRUCache(max_items=1024)
        self._active_requests: set[str] = set()
        self._thread_pool = QThreadPool.globalInstance()
        self.cache_dir = Path(cache_dir) if cache_dir else None

    def set_background_color(self, color) -> None:
        """Set the background color used by the model for items.

        Accepts a QColor, a Qt.GlobalColor, or None to clear.
        """
        if color is None:
            self._background_color = None
            return
        if isinstance(color, QColor):
            self._background_color = color
            return
        try:
            # QColor can accept Qt.GlobalColor values or color names
            self._background_color = QColor(color)
        except Exception:
            # fallback to transparent
            self._background_color = QColor(Qt.transparent)

    def rowCount(
        self, parent: QModelIndex = QModelIndex()
    ) -> int:  # noqa: N802
        return len(self._entries)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._entries):
            return None

        entry = self._entries[index.row()]

        if role == Qt.DisplayRole:
            return entry.display
        if role == Qt.BackgroundRole:
            if self._background_color is None:
                return None
            return QBrush(self._background_color)
        if role == Qt.DecorationRole:
            return QIcon(self._pixmap_for_entry(entry))
        if role == Qt.ToolTipRole:
            return entry.tooltip or entry.path or ""
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignHCenter | Qt.AlignVCenter)
        if role == Qt.SizeHintRole:
            return QSize(self.thumb_size + 32, self.thumb_size + 56)
        if role == Qt.UserRole:
            return entry
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        base_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if not index.isValid():
            return base_flags
        entry = self._entries[index.row()]
        if not entry.is_batch and entry.path:
            base_flags |= Qt.ItemIsDragEnabled
        return base_flags

    def mimeTypes(self) -> List[str]:  # noqa: N802
        return ["text/uri-list", "text/plain"]

    def mimeData(self, indexes: Iterable[QModelIndex]) -> Optional[QMimeData]:
        paths: List[str] = []
        for index in indexes:
            if not index.isValid() or index.row() >= len(self._entries):
                continue
            entry = self._entries[index.row()]
            if entry.is_batch or not entry.path:
                continue
            paths.append(entry.path)

        if not paths:
            return None

        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path) for path in paths])
        mime.setText("\n".join(paths))
        return mime

    def supportedDragActions(self) -> Qt.DropActions:  # noqa: N802
        return Qt.CopyAction

    def set_entries(self, entries: Sequence[GalleryEntry]) -> None:
        """Replace the current entries shown by the model."""

        self.beginResetModel()
        self._entries = list(entries)
        self._active_requests.clear()
        self.endResetModel()

    def clear(self) -> None:
        """Remove all entries from the model."""

        self.beginResetModel()
        self._entries.clear()
        self._active_requests.clear()
        self._cache.clear()
        self.endResetModel()

    def entry_at(self, row: int) -> Optional[GalleryEntry]:
        """Return the entry at ``row`` if it exists."""

        if 0 <= row < len(self._entries):
            return self._entries[row]
        return None

    def _pixmap_for_entry(self, entry: GalleryEntry) -> QPixmap:
        if not entry.path:
            return self._placeholder

        try:
            mtime = float(os.path.getmtime(entry.path))
        except OSError:
            return self._placeholder

        cache_key = self._cache_key(entry.path, mtime)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        self._request_thumbnail(entry.path)
        return self._placeholder

    def _request_thumbnail(self, path: str) -> None:
        if path in self._active_requests:
            return

        job = _ThumbnailJob(path, self.thumb_size, self.cache_dir)
        job.signals.finished.connect(
            self._handle_job_finished, Qt.QueuedConnection
        )
        self._active_requests.add(path)
        self._thread_pool.start(job)

    def _handle_job_finished(
        self, path: str, png_bytes: object, mtime: float
    ) -> None:
        self._active_requests.discard(path)

        pixmap = self._placeholder
        if isinstance(png_bytes, (bytes, bytearray)):
            image = QImage.fromData(png_bytes)
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)

        cache_key = self._cache_key(path, mtime)
        self._cache.put(cache_key, pixmap)

        for row, entry in enumerate(self._entries):
            if entry.path == path:
                index = self.index(row)
                self.dataChanged.emit(index, index, [Qt.DecorationRole])

    def _cache_key(self, path: str, mtime: float) -> str:
        return f"{path}:{mtime}"

    def _make_placeholder(self) -> QPixmap:
        pixmap = QPixmap(self.thumb_size, self.thumb_size)
        pixmap.fill(Qt.transparent)
        return pixmap


__all__ = ["GalleryEntry", "ThumbnailListModel"]
