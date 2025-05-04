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

            self.api.clear_download_status()
            self.api.set_download_status(f"Downloading {file_name}")

            file_name = os.path.expanduser(file_name)
            try:
                os.makedirs(file_name, exist_ok=True)
            except FileExistsError:
                pass

            self.api.update_download_log(
                f"Downloading {url} of size {size_kb} bytes to {file_name}"
            )

            if os.path.exists(file_name):
                self.api.update_download_log(
                    "File already exists, skipping download"
                )
                self.api.set_download_progress(current=size_kb, total=size_kb)
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
                            self.api.set_download_progress(
                                current=f.tell(), total=size_kb
                            )
                            self.progress.emit(f.tell(), size_kb)

                self.api.update_download_log(
                    f"Finished downloading {file_name}"
                )
                self.finished.emit()

            except Exception as e:
                self.failed.emit(e)
                self.api.download_complete()
