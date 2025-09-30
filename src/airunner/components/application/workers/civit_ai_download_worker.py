import os
import time
from queue import Queue
import requests
from PySide6.QtCore import QObject, Signal
from airunner.enums import SignalCode
from airunner.utils.application.mediator_mixin import MediatorMixin


class CivitAIDownloadWorker(MediatorMixin, QObject):
    """
    Worker class for downloading files from CivitAI with progress tracking and cancellation support.
    """

    # Use object-typed signals for progress so very large byte counts do
    # not raise OverflowError when converted to C integers by PySide.
    progress = Signal(object, object)  # current, total
    finished = Signal()
    failed = Signal(Exception)

    def __init__(self, api_key: str = "", *args, **kwargs):
        super().__init__()
        self.queue = Queue()
        self.running = False
        self.is_cancelled = False
        self.api_key = api_key

    def add_to_queue(self, data: tuple):
        """Add a download task to the queue."""
        self.queue.put(data)

    def _auth_headers(self) -> dict:
        """Return Authorization headers if an API key is configured."""
        headers: dict = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @staticmethod
    def get_size(url: str) -> int:
        """Get the size of the file at the given URL in kilobytes."""
        try:
            # Note: HEAD requests won't follow all auth flows, but we add headers for consistency
            response = requests.head(url, allow_redirects=True)
            return int(response.headers.get("content-length", 0))
        except OverflowError:
            raise OverflowError(f"OverflowError when getting size for {url}")

    def cancel(self):
        """Cancel the current download process."""
        self.is_cancelled = True
        self.running = False

    def download(self):
        """Process the download queue and handle file downloads."""
        self.running = True
        while self.running and not self.is_cancelled:
            if self.queue.empty():
                time.sleep(0.1)
                continue

            try:
                url, file_name, size_kb = self.queue.get()
                self._download_file(url, file_name, size_kb)
            except Exception as e:
                self.failed.emit(e)
            finally:
                self.running = False

    def _download_file(self, url: str, file_name: str, size_kb: int):
        """Download a single file with progress tracking."""
        size_bytes = size_kb * 1024
        file_name = os.path.expanduser(file_name)

        self._setup_download_ui(file_name, url, size_bytes)

        if self._file_exists_skip(file_name, size_bytes):
            return

        # Try download with auth header first
        if not self._attempt_download(url, file_name, size_bytes):
            # Retry with token query param on 401
            self._retry_with_token(url, file_name, size_bytes)

    def _setup_download_ui(self, file_name: str, url: str, size_bytes: int):
        """Setup UI signals for download start."""
        self.emit_signal(SignalCode.CLEAR_DOWNLOAD_STATUS_BAR)
        self.emit_signal(
            SignalCode.SET_DOWNLOAD_STATUS_LABEL,
            {"message": f"Downloading {os.path.basename(file_name)}"},
        )
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Downloading {url} to {file_name}"},
        )

        try:
            os.makedirs(os.path.dirname(file_name), exist_ok=True)
        except (FileExistsError, OSError):
            pass

    def _file_exists_skip(self, file_name: str, size_bytes: int) -> bool:
        """Check if file exists and skip download if so."""
        if os.path.exists(file_name):
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": "File already exists, skipping download"},
            )
            self.progress.emit(size_bytes, size_bytes)
            self.finished.emit()
            return True
        return False

    def _attempt_download(
        self, url: str, file_name: str, size_bytes: int
    ) -> bool:
        """Attempt download with auth header. Returns True on success."""
        try:
            headers = self._auth_headers()
            return self._stream_download(url, file_name, size_bytes, headers)
        except requests.HTTPError as e:
            if (
                getattr(getattr(e, "response", None), "status_code", None)
                == 401
            ):
                return False  # Will retry with token
            self.failed.emit(e)
            return True  # Don't retry non-401 errors
        except Exception as e:
            self.failed.emit(e)
            return True

    def _retry_with_token(self, url: str, file_name: str, size_bytes: int):
        """Retry download with token query param on 401."""
        if not self.api_key:
            self.failed.emit(
                Exception("401 Unauthorized and no API key configured")
            )
            return

        sep = "&" if "?" in url else "?"
        token_url = f"{url}{sep}token={self.api_key}"

        try:
            headers = self._auth_headers()
            if not self._stream_download(
                token_url, file_name, size_bytes, headers
            ):
                self.failed.emit(
                    Exception("Download failed after token retry")
                )
        except Exception as e:
            self.failed.emit(e)

    def _stream_download(
        self, url: str, file_name: str, size_bytes: int, headers: dict
    ) -> bool:
        """Stream download with progress tracking. Returns True on success."""
        try:
            with requests.get(
                url,
                stream=True,
                allow_redirects=True,
                headers=headers,
                timeout=30,
            ) as r:
                r.raise_for_status()

                with open(file_name, "wb") as f:
                    downloaded = 0
                    for chunk in r.iter_content(chunk_size=8192):
                        if self.is_cancelled:
                            return False

                        if chunk:  # Filter out keep-alive chunks
                            f.write(chunk)
                            downloaded += len(chunk)
                            self.progress.emit(downloaded, size_bytes)

                if not self.is_cancelled:
                    self.emit_signal(
                        SignalCode.UPDATE_DOWNLOAD_LOG,
                        {
                            "message": f"Finished downloading {os.path.basename(file_name)}"
                        },
                    )
                    self.finished.emit()
                return True

        except requests.RequestException as e:
            raise e
