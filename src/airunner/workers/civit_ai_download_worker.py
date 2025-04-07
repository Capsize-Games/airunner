import os
import time
from queue import Queue
import requests
from PySide6.QtCore import QObject, Signal
from airunner.enums import SignalCode
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin


class CivitAIDownloadWorker(MediatorMixin, SettingsMixin, QObject):
    """
    Worker class for downloading files from CivitAI with progress tracking and cancellation support.
    """

    progress = Signal(int, int)  # current, total
    finished = Signal()
    failed = Signal(Exception)

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.queue = Queue()
        self.running = False
        self.is_cancelled = False

    def add_to_queue(self, data: tuple):
        """Add a download task to the queue."""
        self.queue.put(data)

    @staticmethod
    def get_size(url: str) -> int:
        """Get the size of the file at the given URL in kilobytes."""
        try:
            response = requests.head(url, allow_redirects=True)
            return int(response.headers.get("content-length", 0))
        except OverflowError:
            raise OverflowError(f"OverflowError when getting size for {url}")

    def cancel(self):
        """Cancel the current download process."""
        self.is_cancelled = True

    def download(self):
        """Process the download queue and handle file downloads."""
        self.running = True
        while self.running:
            if self.queue.empty():
                time.sleep(0.1)
                continue

            url, file_name, size_kb = self.queue.get()
            size_kb *= 1024  # Convert size from KB to bytes

            self.emit_signal(SignalCode.CLEAR_DOWNLOAD_STATUS_BAR)
            self.emit_signal(
                SignalCode.SET_DOWNLOAD_STATUS_LABEL,
                {"message": f"Downloading {file_name}"},
            )

            file_name = os.path.expanduser(file_name)
            try:
                os.makedirs(os.path.dirname(file_name), exist_ok=True)
            except FileExistsError:
                pass

            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {
                    "message": f"Downloading {url} of size {size_kb} bytes to {file_name}"
                },
            )

            if os.path.exists(file_name):
                self.emit_signal(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    {"message": "File already exists, skipping download"},
                )
                self.emit_signal(
                    SignalCode.DOWNLOAD_PROGRESS,
                    {"current": size_kb, "total": size_kb},
                )
                self.progress.emit(size_kb, size_kb)
                self.finished.emit()
                continue

            try:
                with requests.get(url, stream=True, allow_redirects=True) as r:
                    r.raise_for_status()
                    with open(file_name, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if self.is_cancelled:
                                break
                            f.write(chunk)
                            self.emit_signal(
                                SignalCode.DOWNLOAD_PROGRESS,
                                {"current": f.tell(), "total": size_kb},
                            )
                            self.progress.emit(f.tell(), size_kb)

                self.emit_signal(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    {"message": f"Finished downloading {file_name}"},
                )
                self.finished.emit()

            except Exception as e:
                self.failed.emit(e)
                self.emit_signal(SignalCode.DOWNLOAD_COMPLETE)
