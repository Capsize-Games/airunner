import os
from queue import Queue
import time
import requests
from PySide6.QtCore import QObject, Signal
from airunner.enums import SignalCode
from airunner.mediator_mixin import MediatorMixin
from airunner.windows.main.settings_mixin import SettingsMixin


class CivitAIDownloadWorker(
    QObject,
    MediatorMixin,
    SettingsMixin
):
    progress = Signal(int, int)  # current, total
    finished = Signal()
    failed = Signal(Exception)
    queue = Queue()
    running = False
    is_cancelled = False

    def __init__(self, *args, **kwargs):
        MediatorMixin.__init__(self)
        
        super(CivitAIDownloadWorker, self).__init__(*args, **kwargs)

    def add_to_queue(self, data: tuple):
        self.queue.put(data)

    def get_size(self, url: str):
        try:
            response = requests.head(url, allow_redirects=True)
            size_kb = int(response.headers.get("content-length", 0))
            return size_kb
        except OverflowError:
            print(f"OverflowError when getting size for {url}")
            raise

    def cancel(self):
        self.is_cancelled = True

    def download(self):
        self.running = True

        while self.running:
            if self.queue.empty():
                time.sleep(0.1)
                continue
            url, file_name, size_kb = self.queue.get()
            # convert size_kb to bytes
            size_kb = size_kb * 1024
            self.emit_signal(SignalCode.CLEAR_DOWNLOAD_STATUS_BAR)

            self.emit_signal(SignalCode.SET_DOWNLOAD_STATUS_LABEL, {
                "message": f"Downloading {file_name}"
            })

            file_name = os.path.join(file_name)
            file_name = os.path.expanduser(file_name)

            if not os.path.exists(os.path.dirname(file_name)):
                os.makedirs(os.path.dirname(file_name), exist_ok=True)

            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {
                    "message": f"Downloading {url} of size {size_kb} KB to {file_name}"
                }
            )

            if os.path.exists(file_name):
                self.emit_signal(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    {
                        "message":  f"File already exists, skipping download"
                    }
                )
                self.emit_signal(SignalCode.DOWNLOAD_PROGRESS, {
                    "current": size_kb,
                    "total": size_kb
                })
                self.progress.emit(size_kb, size_kb)
                self.finished.emit()
                continue

            try:
                headers = {}
                with requests.get(url, headers=headers, stream=True, allow_redirects=True) as r:
                    r.raise_for_status()
                    dir_name = os.path.dirname(file_name)

                    if dir_name != "" and not os.path.exists(dir_name):
                        os.makedirs(dir_name, exist_ok=True)

                    with open(file_name, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if self.is_cancelled:
                                break
                            try:
                                f.write(chunk)
                            except OverflowError:
                                print(f"OverflowError when writing to {file_name}")
                                raise
                            self.emit_signal(SignalCode.DOWNLOAD_PROGRESS, {
                                "current": f.tell(),
                                "total": size_kb
                            })
                            self.progress.emit(f.tell(), size_kb)
                        self.emit_signal(
                            SignalCode.UPDATE_DOWNLOAD_LOG,
                            {
                                "message": f"finished with download of {file_name}"
                            }
                        )
                        self.finished.emit()
            except Exception as e:
                print(f"Failed to download {url}")
                print(e)
                self.failed.emit(e)
                self.emit_signal(SignalCode.DOWNLOAD_COMPLETE)
