"""Worker that downloads a single file and reports progress.

Refactored version with focused helper methods for maintainability.
"""

import os
from typing import Dict, Optional, Callable, Tuple
import requests
from PySide6.QtCore import Signal
from airunner.enums import SignalCode
from airunner.components.application.workers.worker import Worker
from airunner.settings import DEFAULT_HF_ENDPOINT


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

    # Constants
    MAX_SAFE_VALUE = 2147483647  # 32-bit signed integer max
    SCALE_FACTOR = 1000000  # Scale to MB for overflow handling

    def get_size(self, url: str) -> int:
        """Return size in bytes for a URL or 0 if unknown.

        Args:
            url: URL to check

        Returns:
            File size in bytes or 0 if unknown
        """
        try:
            response = requests.head(url, allow_redirects=True, timeout=30)
            content_length = response.headers.get("content-length", "0")
            try:
                return int(content_length)
            except (ValueError, OverflowError):
                self.logger.warning(
                    "Invalid or oversized content-length: %s for %s",
                    content_length,
                    url,
                )
                return 0
        except OverflowError:  # extremely unlikely
            self.logger.exception(
                "OverflowError when getting size for %s", url
            )
            return 0
        except Exception:  # size retrieval failure is non-fatal
            self.logger.exception("Failed to get size for %s", url)
            return 0

    def cancel(self) -> None:
        """Cancel the current download operation."""
        self.is_cancelled = True

    def _safe_download_complete(self, file_name: str) -> None:
        """Safely call download_complete callback if available.

        Args:
            file_name: Path to downloaded file
        """
        api = getattr(self, "api", None)
        if api and hasattr(api, "download_complete"):
            try:
                api.download_complete(file_name)
            except Exception:
                self.logger.exception(
                    "download_complete callback failed for %s", file_name
                )

    def handle_message(self, data: Dict) -> None:
        """Handle download request message.

        Args:
            data: Download request data containing path, file_name, file_path,
                and optional callback
        """
        try:
            # Extract and validate parameters
            params = self._extract_parameters(data)
            if not params:
                self.finished.emit({})
                return

            path, file_name, file_path, callback = params

            # Build download URL
            url = self._build_download_url(path, file_name)

            # Prepare file path
            file_name_full = self._prepare_file_path(file_path, file_name)

            # Get file size
            size_bytes = self.get_size(url)

            # Check if file already exists
            if self._handle_existing_file(
                file_name_full, size_bytes, callback
            ):
                return

            # Log download start
            self._log_download_start(url, file_name_full, size_bytes)

            # Build request headers
            headers = self._build_request_headers()

            # Execute download
            self._execute_download(
                url, file_name_full, size_bytes, headers, callback
            )

        finally:
            self.emit_signal(
                SignalCode.DOWNLOAD_COMPLETE,
                {
                    "file_name": (
                        file_name_full if "file_name_full" in locals() else ""
                    )
                },
            )

    def _extract_parameters(
        self, data: Dict
    ) -> Optional[Tuple[str, str, str, Optional[Callable]]]:
        """Extract and validate download parameters.

        Args:
            data: Download request data

        Returns:
            Tuple of (path, file_name, file_path, callback) or None if invalid
        """
        path = data.get("requested_path", "")
        file_name = data.get("requested_file_name", "")
        file_path = data.get("requested_file_path", "")
        callback = data.get("requested_callback")

        if not (path or file_name or file_path):
            if callable(callback):
                try:
                    callback(0, 0)
                except Exception:
                    self.logger.exception(
                        "Progress callback failed (empty request)"
                    )
            return None

        return path, file_name, file_path, callback

    def _build_download_url(self, path: str, file_name: str) -> str:
        """Build Hugging Face download URL.

        Args:
            path: Model path on Hugging Face
            file_name: Name of file to download

        Returns:
            Complete download URL
        """
        url = f"{DEFAULT_HF_ENDPOINT}/{path}/resolve/main/{file_name}?download=true"
        return url.replace(" ", "")

    def _prepare_file_path(self, file_path: str, file_name: str) -> str:
        """Prepare full file path and ensure directory exists.

        Args:
            file_path: Directory path
            file_name: File name

        Returns:
            Full file path (expanded)
        """
        file_name_full = os.path.join(file_path, file_name)
        file_name_full = os.path.expanduser(file_name_full)
        dir_path = os.path.dirname(file_name_full)

        if dir_path and not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
            except FileExistsError:
                pass

        return file_name_full

    def _handle_existing_file(
        self,
        file_name_full: str,
        size_bytes: int,
        callback: Optional[Callable],
    ) -> bool:
        """Check if file exists and handle skip case.

        Args:
            file_name_full: Full path to file
            size_bytes: Expected file size
            callback: Optional progress callback

        Returns:
            True if file exists and download should be skipped
        """
        if not os.path.exists(file_name_full):
            return False

        # Emit progress as complete
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
                self.logger.exception(
                    "Progress callback failed after skip for %s",
                    file_name_full,
                )

        self.finished.emit({})
        return True

    def _log_download_start(
        self, url: str, file_name_full: str, size_bytes: int
    ):
        """Log download start message.

        Args:
            url: Download URL
            file_name_full: Full path to file
            size_bytes: File size in bytes
        """
        self.emit_signal(SignalCode.CLEAR_DOWNLOAD_STATUS_BAR)
        self.emit_signal(
            SignalCode.SET_DOWNLOAD_STATUS_LABEL,
            {"message": f"Downloading {os.path.basename(file_name_full)}"},
        )

        human_size = self._format_file_size(size_bytes)
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {
                "message": f"Downloading {url} ({human_size}) to {file_name_full}"
            },
        )

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string
        """
        if not size_bytes:
            return "unknown size"

        try:
            if size_bytes < 1024 * 1024:  # < 1MB
                return f"{size_bytes/1024:.2f} KB"
            else:  # >= 1MB
                return f"{size_bytes/(1024*1024):.2f} MB"
        except (OverflowError, ZeroDivisionError):
            # For very large files, use GB
            try:
                return f"{size_bytes/(1024*1024*1024):.2f} GB"
            except (OverflowError, ZeroDivisionError):
                return "very large file"

    def _build_request_headers(self) -> Dict[str, str]:
        """Build HTTP request headers with optional authentication.

        Returns:
            Headers dictionary
        """
        headers = {}
        token = (
            os.getenv("AIRUNNER_HF_TOKEN")
            or os.getenv("HF_TOKEN")
            or os.getenv("HUGGINGFACE_TOKEN")
        )
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _execute_download(
        self,
        url: str,
        file_name_full: str,
        size_bytes: int,
        headers: Dict[str, str],
        callback: Optional[Callable],
    ):
        """Execute file download with progress tracking.

        Args:
            url: Download URL
            file_name_full: Full path to save file
            size_bytes: Expected file size
            headers: Request headers
            callback: Optional progress callback
        """
        try:
            with requests.get(
                url,
                stream=True,
                allow_redirects=True,
                timeout=60,
                headers=headers,
            ) as r:
                # Handle HTTP errors
                if not self._handle_response_status(r):
                    return

                # Ensure directory exists
                self._ensure_directory_exists(file_name_full)

                # Download file
                written = self._download_file_chunks(
                    r, file_name_full, size_bytes, callback
                )
                if written is None:  # Cancelled
                    return

                # Log completion
                self._log_download_complete(file_name_full)

                # Call completion callbacks
                self._handle_download_completion(
                    file_name_full, size_bytes, written, callback
                )

                self.finished.emit({})

        except Exception as e:
            self.logger.exception("Failed to download %s", url)
            self.failed.emit(e)

    def _handle_response_status(self, response: requests.Response) -> bool:
        """Handle HTTP response status codes.

        Args:
            response: HTTP response object

        Returns:
            True if status is OK, False if should abort
        """
        try:
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
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
                return False
            raise

    def _ensure_directory_exists(self, file_name_full: str):
        """Ensure directory for file exists.

        Args:
            file_name_full: Full path to file
        """
        dir_path = os.path.dirname(file_name_full)
        if dir_path and not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
            except FileExistsError:
                pass

    def _download_file_chunks(
        self,
        response: requests.Response,
        file_name_full: str,
        size_bytes: int,
        callback: Optional[Callable],
    ) -> Optional[int]:
        """Download file in chunks with progress tracking.

        Args:
            response: HTTP response object
            file_name_full: Full path to file
            size_bytes: Expected file size
            callback: Optional progress callback

        Returns:
            Total bytes written or None if cancelled
        """
        written = 0
        callback_active = callback  # Track if callback is still usable

        with open(file_name_full, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if self.is_cancelled:
                    self.emit_signal(
                        SignalCode.UPDATE_DOWNLOAD_LOG,
                        {"message": f"Download cancelled: {file_name_full}"},
                    )
                    return None

                if not chunk:
                    continue

                try:
                    f.write(chunk)
                except OverflowError:
                    self.logger.exception(
                        "OverflowError when writing %s", file_name_full
                    )
                    raise

                written = f.tell()

                # Update progress
                callback_active = self._update_download_progress(
                    written, size_bytes, file_name_full, callback_active
                )

        return written

    def _update_download_progress(
        self,
        written: int,
        size_bytes: int,
        file_name_full: str,
        callback: Optional[Callable],
    ) -> Optional[Callable]:
        """Update download progress via signals and callback.

        Args:
            written: Bytes written so far
            size_bytes: Total file size
            file_name_full: Full path to file
            callback: Optional progress callback

        Returns:
            Callback (or None if disabled due to errors)
        """
        effective_total = size_bytes if size_bytes else written or 1

        # Emit signal
        self._emit_progress_signal(written, effective_total, file_name_full)

        # Call callback if provided
        if callable(callback):
            return self._invoke_progress_callback(
                callback, written, effective_total, file_name_full
            )

        return callback

    def _emit_progress_signal(
        self, written: int, effective_total: int, file_name_full: str
    ):
        """Emit progress signal with overflow handling.

        Args:
            written: Bytes written
            effective_total: Total bytes
            file_name_full: Full path to file
        """
        try:
            self.emit_signal(
                SignalCode.DOWNLOAD_PROGRESS,
                {"current": written, "total": effective_total},
            )
        except OverflowError:
            self.logger.warning(
                "OverflowError in progress signal for large file %s (written=%d, total=%d)",
                file_name_full,
                written,
                effective_total,
            )
            # Emit scaled-down progress
            self.emit_signal(
                SignalCode.DOWNLOAD_PROGRESS,
                {
                    "current": written // self.SCALE_FACTOR,
                    "total": effective_total // self.SCALE_FACTOR,
                },
            )

    def _invoke_progress_callback(
        self,
        callback: Callable,
        written: int,
        effective_total: int,
        file_name_full: str,
    ) -> Optional[Callable]:
        """Invoke progress callback with overflow handling.

        Args:
            callback: Progress callback function
            written: Bytes written
            effective_total: Total bytes
            file_name_full: Full path to file

        Returns:
            Callback (or None if disabled due to errors)
        """
        # Pre-emptively scale down very large values
        safe_written, safe_total = self._scale_progress_values(
            written, effective_total
        )

        # Try normal callback
        if self._try_callback(callback, safe_written, safe_total):
            return callback

        # Try aggressive scaling on overflow
        self.logger.warning(
            "OverflowError in progress callback for large file %s",
            file_name_full,
        )
        return self._retry_callback_with_aggressive_scaling(
            callback, written, effective_total, file_name_full
        )

    def _try_callback(
        self, callback: Callable, safe_written: int, safe_total: int
    ) -> bool:
        """Try to call callback with given values.

        Args:
            callback: Callback function
            safe_written: Bytes written (scaled if needed)
            safe_total: Total bytes (scaled if needed)

        Returns:
            True if successful
        """
        try:
            callback(int(safe_written), int(safe_total))
            return True
        except (OverflowError, ValueError):
            return False
        except Exception:
            return False

    def _retry_callback_with_aggressive_scaling(
        self,
        callback: Callable,
        written: int,
        effective_total: int,
        file_name_full: str,
    ) -> Optional[Callable]:
        """Retry callback with aggressive value scaling.

        Args:
            callback: Callback function
            written: Original bytes written
            effective_total: Original total bytes
            file_name_full: Full path to file

        Returns:
            Callback (or None if still failing)
        """
        try:
            safe_written = max(0, min(1000000, written // self.SCALE_FACTOR))
            safe_total = max(
                1, min(1000000, effective_total // self.SCALE_FACTOR)
            )
            callback(safe_written, safe_total)
            return callback
        except Exception:
            self.logger.exception(
                "Progress callback failed even with aggressive scaling for %s",
                file_name_full,
            )
            return None

    def _scale_progress_values(
        self, written: int, effective_total: int
    ) -> Tuple[int, int]:
        """Scale down large progress values to safe range.

        Args:
            written: Bytes written
            effective_total: Total bytes

        Returns:
            Tuple of (safe_written, safe_total)
        """
        if (
            written > self.MAX_SAFE_VALUE
            or effective_total > self.MAX_SAFE_VALUE
        ):
            scale = max(written, effective_total) // self.MAX_SAFE_VALUE + 1
            return written // scale, effective_total // scale
        return written, effective_total

    def _log_download_complete(self, file_name_full: str):
        """Log download completion.

        Args:
            file_name_full: Full path to file
        """
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Finished download: {file_name_full}"},
        )
        self._safe_download_complete(file_name_full)

    def _handle_download_completion(
        self,
        file_name_full: str,
        size_bytes: int,
        written: int,
        callback: Optional[Callable],
    ):
        """Handle download completion callbacks.

        Args:
            file_name_full: Full path to file
            size_bytes: Expected file size
            written: Actual bytes written
            callback: Optional completion callback
        """
        if not callable(callback):
            return

        final_total = size_bytes if size_bytes else written

        # Pre-emptively scale completion values
        if final_total > self.MAX_SAFE_VALUE:
            scale = final_total // self.MAX_SAFE_VALUE + 1
            final_total = final_total // scale

        try:
            callback(int(final_total), int(final_total))
        except (OverflowError, ValueError):
            self.logger.warning(
                "OverflowError in completion callback for large file %s",
                file_name_full,
            )
            self._retry_completion_callback_scaled(
                callback, size_bytes, written, file_name_full
            )
        except Exception:
            self.logger.exception(
                "Download callback failed at completion for %s",
                file_name_full,
            )

    def _retry_completion_callback_scaled(
        self,
        callback: Callable,
        size_bytes: int,
        written: int,
        file_name_full: str,
    ):
        """Retry completion callback with aggressive scaling.

        Args:
            callback: Completion callback
            size_bytes: Expected file size
            written: Actual bytes written
            file_name_full: Full path to file
        """
        try:
            safe_final = max(
                1,
                min(
                    1000000,
                    (size_bytes if size_bytes else written)
                    // self.SCALE_FACTOR,
                ),
            )
            callback(safe_final, safe_final)
        except Exception:
            self.logger.exception(
                "Completion callback failed even with aggressive scaling for %s",
                file_name_full,
            )
