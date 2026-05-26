"""Qt workers for the daemon-backed CivitAI browser."""

from __future__ import annotations

import os
import time
from typing import Optional

from PySide6.QtCore import QObject, Signal

from airunner.daemon_client.gui_daemon_client import GuiDaemonClient
from airunner_model.url_safety import safe_fetch_bytes

_IMAGE_MAX_BYTES = 5_000_000


class ModelSearchWorker(QObject):
    """Fetch one filtered CivitAI search payload in a worker thread."""

    fetched = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        *,
        query: str = "",
        base_models: Optional[list[str]] = None,
        model_types: Optional[list[str]] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
        api_key: str = "",
    ) -> None:
        super().__init__()
        self._client = GuiDaemonClient()
        self._query = query
        self._base_models = base_models
        self._model_types = model_types
        self._limit = limit
        self._cursor = cursor
        self._api_key = api_key

    def run(self) -> None:
        """Fetch one browser search payload and emit the result."""
        try:
            payload = self._client.search_civitai_models(
                query=self._query,
                base_models=self._base_models,
                model_types=self._model_types,
                limit=self._limit,
                cursor=self._cursor,
                api_key=self._api_key,
            )
            self.fetched.emit(payload)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class ModelInfoWorker(QObject):
    """Fetch one filtered CivitAI model payload in a worker thread."""

    fetched = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        *,
        model_id: str,
        base_models: Optional[list[str]] = None,
        model_types: Optional[list[str]] = None,
        api_key: str = "",
    ) -> None:
        super().__init__()
        self._client = GuiDaemonClient()
        self._model_id = model_id
        self._base_models = base_models
        self._model_types = model_types
        self._api_key = api_key

    def run(self) -> None:
        """Fetch one browser detail payload and emit the result."""
        try:
            payload = self._client.fetch_civitai_model(
                model_id=self._model_id,
                base_models=self._base_models,
                model_types=self._model_types,
                api_key=self._api_key,
            )
            self.fetched.emit(payload)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class FileDownloadWorker(QObject):
    """Mirror one daemon-backed CivitAI download job into Qt signals."""

    progress = Signal(object, object)
    finished = Signal(str)
    error = Signal(str)
    canceled = Signal()

    def __init__(
        self,
        *,
        url: str,
        save_path: str,
        api_key: str = "",
        total_size_bytes: int = 0,
    ) -> None:
        super().__init__()
        self._client = GuiDaemonClient(poll_interval_seconds=0.10)
        self.url = url
        self.save_path = os.path.expanduser(save_path)
        self._api_key = api_key
        self._total_size = max(0, int(total_size_bytes))
        self._cancelled = False
        self._job_id: Optional[str] = None

    def cancel(self) -> None:
        """Request cancellation for one active daemon job."""
        self._cancelled = True
        if self._job_id is None:
            return
        try:
            self._client.cancel_download_job(self._job_id)
        except Exception:
            return

    def run(self) -> None:
        """Start one daemon download job and poll until it finishes."""
        try:
            response = self._client.start_civitai_file_download(
                url=self.url,
                output_path=self.save_path,
                file_size=self._total_size,
                api_key=self._api_key or None,
            )
            self._job_id = str(response.get("job_id") or "")
            if not self._job_id:
                self.error.emit("Missing CivitAI download job id")
                return
            self._poll_job()
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))

    def _poll_job(self) -> None:
        """Poll one daemon job and forward progress updates to the GUI."""
        last_current = -1
        while True:
            status = self._client.download_job_status(self._job_id or "")
            state = str(status.get("status", "")).lower()
            progress = float(status.get("progress") or 0.0)
            current = self._current_bytes(progress)
            if current != last_current:
                last_current = current
                self.progress.emit(current, self._total_size)
            if state == "completed":
                self.finished.emit(self.save_path)
                return
            if state == "failed":
                self.error.emit(
                    str(status.get("error") or "Download failed")
                )
                return
            if state == "cancelled":
                self.canceled.emit()
                return
            time.sleep(0.10)

    def _current_bytes(self, progress: float) -> int:
        """Convert one percentage to a byte count for the progress UI."""
        if self._total_size <= 0:
            return 0
        clamped = max(0.0, min(100.0, progress))
        return int(round((clamped / 100.0) * self._total_size))


class ImageLoaderWorker(QObject):
    """Fetch and cache one remote image through the safe-fetch helper."""

    loaded = Signal(str, str)
    error = Signal(str, str)

    def __init__(
        self,
        *,
        key: str,
        url: str,
        cache_path: str,
        max_bytes: int = _IMAGE_MAX_BYTES,
    ) -> None:
        super().__init__()
        self._key = key
        self._url = url
        self._cache_path = cache_path
        self._max_bytes = max_bytes

    def run(self) -> None:
        """Fetch one image into the cache and emit the saved file path."""
        try:
            if not os.path.exists(self._cache_path):
                os.makedirs(
                    os.path.dirname(self._cache_path),
                    exist_ok=True,
                )
                payload = safe_fetch_bytes(
                    self._url,
                    max_bytes=self._max_bytes,
                )
                with open(self._cache_path, "wb") as file_pointer:
                    file_pointer.write(payload)
            self.loaded.emit(self._key, self._cache_path)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(self._key, str(exc))
