import os
import requests
from PySide6.QtCore import QObject, Signal

from airunner.aihandler.logger import Logger

logger = Logger(prefix="DownloadWorker")

class DownloadWorker(QObject):
    progress = Signal(int, int)  # current, total
    finished = Signal()
    failed = Signal(Exception)

    def __init__(self, url, file_name, size_kb):
        super().__init__()
        self.url = url
        self.file_name = file_name
        self.size_bytes = size_kb * 1024
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def download(self):
        logger.debug(f"Downloading {self.url} to {self.file_name}")
        try:
            with requests.get(self.url, stream=True) as r:
                logger.debug(f"request {r}")
                r.raise_for_status()
                dir_name = os.path.dirname(self.file_name)
                logger.debug(f"creating directory {dir_name}")
                os.makedirs(dir_name, exist_ok=True)

                logger.debug(f"Writing filename {self.file_name}")
                with open(self.file_name, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if self.is_cancelled:
                            break
                        f.write(chunk)
                        self.progress.emit(f.tell(), self.size_bytes)
            if not self.is_cancelled:
                self.finished.emit()
        except Exception as e:
            self.failed.emit(e)
