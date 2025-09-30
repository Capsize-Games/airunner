import os
import logging
from typing import Dict, Optional, Callable
import requests
from PySide6.QtCore import Signal
from airunner.enums import SignalCode
from airunner.components.application.workers.worker import Worker
from airunner.settings import DEFAULT_HF_ENDPOINT

logger = logging.getLogger(__name__)


class DownloadWorker(Worker):
    """Worker that downloads a single file and reports progress.

    Emits:
        progress(int, int): Deprecated (use SignalCode.DOWNLOAD_PROGRESS).
        finished(dict): Emitted when the download completes or is skipped.
        failed(Exception): Emitted on error.
    """

    # Use object-typed signal to avoid OverflowError when emitting very
    # large byte counts. Receivers should accept Python ints (unbounded).
    progress = Signal(object, object)  # current, total (legacy)
    finished = Signal(dict)
    failed = Signal(Exception)
    running = False
    is_cancelled = False

    @staticmethod
    def get_size(url: str) -> int:
        """Return size in bytes for a URL or 0 if unknown."""
        try:
            response = requests.head(url, allow_redirects=True, timeout=30)
            content_length = response.headers.get("content-length", "0")
            try:
                return int(content_length)
            except (ValueError, OverflowError):
                logger.warning(
                    "Invalid or oversized content-length: %s for %s",
                    content_length,
                    url,
                )
                return 0
        except OverflowError:  # extremely unlikely
            logger.exception("OverflowError when getting size for %s", url)
            return 0
        except Exception:  # size retrieval failure is non-fatal
            logger.exception("Failed to get size for %s", url)
            return 0

    def cancel(self) -> None:
        self.is_cancelled = True

    def _safe_download_complete(self, file_name: str) -> None:
        api = getattr(self, "api", None)  # type: Optional[object]
        if api and hasattr(api, "download_complete"):
            try:
                api.download_complete(file_name)
            except Exception:
                logger.exception(
                    "download_complete callback failed for %s", file_name
                )

    def handle_message(self, data: Dict) -> None:  # noqa: C901 (keep lean)
        try:
            path = data.get("requested_path", "")
            file_name = data.get("requested_file_name", "")
            file_path = data.get("requested_file_path", "")
            # Progress callback expects signature (current:int, total:int)
            callback: Optional[Callable[[int, int], None]] = data.get(
                "requested_callback"
            )

            if not (path or file_name or file_path):
                if callable(callback):
                    # Nothing to do, emit zero progress
                    try:
                        callback(0, 0)
                    except Exception:
                        logger.exception(
                            "Progress callback failed (empty request)"
                        )
                self.finished.emit({})
                return

            url = f"{DEFAULT_HF_ENDPOINT}/{path}/resolve/main/{file_name}?download=true".replace(
                " ", ""
            )
            self.emit_signal(SignalCode.CLEAR_DOWNLOAD_STATUS_BAR)
            self.emit_signal(
                SignalCode.SET_DOWNLOAD_STATUS_LABEL,
                {"message": f"Downloading {file_name}"},
            )

            file_name_full = os.path.join(file_path, file_name)
            file_name_full = os.path.expanduser(file_name_full)
            dir_path = os.path.dirname(file_name_full)
            if dir_path and not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except FileExistsError:
                    pass

            # Get file size before checking existence
            size_bytes = self.get_size(url)

            if os.path.exists(file_name_full):
                # Emit progress as complete - use size_bytes if available, otherwise use 1/1
                progress_current = size_bytes if size_bytes > 0 else 1
                progress_total = size_bytes if size_bytes > 0 else 1
                self.emit_signal(
                    SignalCode.DOWNLOAD_PROGRESS,
                    {"current": progress_current, "total": progress_total},
                )
                self._safe_download_complete(file_name_full)
                if callable(callback):
                    try:
                        callback(progress_current, progress_total)
                    except Exception:
                        logger.exception(
                            "Progress callback failed after skip for %s",
                            file_name_full,
                        )
                self.finished.emit({})
                return

            try:
                human_size = (
                    f"{size_bytes/1024:.2f} KB"
                    if size_bytes
                    else "unknown size"
                )
            except OverflowError:
                # For very large files, use GB instead
                try:
                    human_size = f"{size_bytes/(1024*1024*1024):.2f} GB"
                except (OverflowError, ZeroDivisionError):
                    human_size = "very large file"

            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {
                    "message": f"Downloading {url} ({human_size}) to {file_name_full}"
                },
            )

            # Build headers (support optional Hugging Face token)
            headers = {}
            token = (
                os.getenv("AIRUNNER_HF_TOKEN")
                or os.getenv("HF_TOKEN")
                or os.getenv("HUGGINGFACE_TOKEN")
            )
            if token:
                headers["Authorization"] = f"Bearer {token}"

            try:
                with requests.get(
                    url,
                    stream=True,
                    allow_redirects=True,
                    timeout=60,
                    headers=headers,
                ) as r:
                    try:
                        r.raise_for_status()
                    except requests.exceptions.HTTPError as e:
                        if (
                            e.response is not None
                            and e.response.status_code == 401
                        ):
                            self.emit_signal(
                                SignalCode.UPDATE_DOWNLOAD_LOG,
                                {
                                    "message": (
                                        "Unauthorized (401). A Hugging Face token may be required. "
                                        "Set AIRUNNER_HF_TOKEN or HF_TOKEN and retry."
                                    )
                                },
                            )
                            self.failed.emit(e)
                            return
                        raise
                    if dir_path and not os.path.exists(dir_path):
                        try:
                            os.makedirs(dir_path, exist_ok=True)
                        except FileExistsError:
                            pass

                    written = 0
                    with open(file_name_full, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if self.is_cancelled:
                                self.emit_signal(
                                    SignalCode.UPDATE_DOWNLOAD_LOG,
                                    {
                                        "message": f"Download cancelled: {file_name_full}"
                                    },
                                )
                                break
                            if not chunk:
                                continue
                            try:
                                f.write(chunk)
                            except OverflowError:
                                logger.exception(
                                    "OverflowError when writing %s",
                                    file_name_full,
                                )
                                raise
                            written = f.tell()
                            # If total size unknown (size_bytes==0), use written as total to allow % progress
                            effective_total = (
                                size_bytes if size_bytes else written or 1
                            )

                            # Safeguard against overflow for very large files
                            try:
                                self.emit_signal(
                                    SignalCode.DOWNLOAD_PROGRESS,
                                    {
                                        "current": written,
                                        "total": effective_total,
                                    },
                                )
                            except OverflowError:
                                logger.warning(
                                    "OverflowError in progress signal for large file %s (written=%d, total=%d)",
                                    file_name_full,
                                    written,
                                    effective_total,
                                )
                                # Emit scaled-down progress to avoid overflow
                                scale = 1000000  # Scale to MB
                                self.emit_signal(
                                    SignalCode.DOWNLOAD_PROGRESS,
                                    {
                                        "current": written // scale,
                                        "total": effective_total // scale,
                                    },
                                )

                            if callable(
                                callback
                            ):  # mirror progress externally
                                # Pre-emptively scale down very large values
                                MAX_SAFE_VALUE = (
                                    2147483647  # 32-bit signed integer max
                                )
                                safe_written = written
                                safe_total = effective_total

                                if (
                                    written > MAX_SAFE_VALUE
                                    or effective_total > MAX_SAFE_VALUE
                                ):
                                    scale = (
                                        max(written, effective_total)
                                        // MAX_SAFE_VALUE
                                        + 1
                                    )
                                    safe_written = written // scale
                                    safe_total = effective_total // scale

                                try:
                                    callback(
                                        int(safe_written), int(safe_total)
                                    )
                                except (OverflowError, ValueError):
                                    logger.warning(
                                        "OverflowError in progress callback for large file %s",
                                        file_name_full,
                                    )
                                    # Try with even more aggressive scaling
                                    try:
                                        scale = 1000000  # Scale to MB
                                        safe_written = max(
                                            0, min(1000000, written // scale)
                                        )
                                        safe_total = max(
                                            1,
                                            min(
                                                1000000,
                                                effective_total // scale,
                                            ),
                                        )
                                        callback(safe_written, safe_total)
                                    except Exception:
                                        logger.exception(
                                            "Progress callback failed even with aggressive scaling for %s",
                                            file_name_full,
                                        )
                                        callback = None  # type: ignore
                                except Exception:
                                    # Log once and disable further callback attempts
                                    logger.exception(
                                        "Progress callback failed during download for %s",
                                        file_name_full,
                                    )
                                    callback = None  # type: ignore

                    if self.is_cancelled:
                        return

                self.emit_signal(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    {"message": f"Finished download: {file_name_full}"},
                )
                self._safe_download_complete(file_name_full)
                if callable(callback):
                    final_total = size_bytes if size_bytes else written
                    MAX_SAFE_VALUE = 2147483647  # 32-bit signed integer max

                    # Pre-emptively scale completion values
                    if final_total > MAX_SAFE_VALUE:
                        scale = final_total // MAX_SAFE_VALUE + 1
                        final_total = final_total // scale

                    try:
                        callback(int(final_total), int(final_total))
                    except (OverflowError, ValueError):
                        logger.warning(
                            "OverflowError in completion callback for large file %s",
                            file_name_full,
                        )
                        # Try with aggressive scaling
                        try:
                            scale = 1000000  # Scale to MB
                            safe_final = max(
                                1,
                                min(
                                    1000000,
                                    (size_bytes if size_bytes else written)
                                    // scale,
                                ),
                            )
                            callback(safe_final, safe_final)
                        except Exception:
                            logger.exception(
                                "Completion callback failed even with aggressive scaling for %s",
                                file_name_full,
                            )
                    except Exception:
                        logger.exception(
                            "Download callback failed at completion for %s",
                            file_name_full,
                        )
                self.finished.emit({})
            except Exception as e:  # network or IO error
                logger.exception("Failed to download %s", url)
                self.failed.emit(e)
        finally:
            # Do not modify self.running here; allow Worker.run loop to continue
            self.emit_signal(
                SignalCode.DOWNLOAD_COMPLETE, {"file_name": file_name_full}
            )
