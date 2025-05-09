
import os
from queue import Queue
import time
from typing import Tuple, Callable

import requests
from PySide6.QtCore import QObject, Signal

from airunner.enums import SignalCode
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin

DEFAULT_HF_ENDPOINT = "https://huggingface.co"


class DownloadWorker(
    MediatorMixin,
    SettingsMixin,
    QObject,
):
    progress: Signal = Signal(int, int)  # current, total
    finished: Signal = Signal()
    failed: Signal = Signal(Exception)
    queue: Queue[Tuple[str, str, str, Callable[[], None]]] = Queue()
    running: bool = False
    is_cancelled: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__()

    def add_to_queue(self, data: tuple):
        self.queue.put(data)

    @staticmethod
    def get_size(url: str):
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

            path, file_name, file_path, callback = self.queue.get()
            if path == "" and file_name == "" and file_path == "":
                callback()
                return
            url = f"{DEFAULT_HF_ENDPOINT}/{path}/resolve/main/{file_name}?download=true".replace(
                " ", ""
            )
            self.api.clear_download_status()
            self.api.set_download_status(f"Downloading {file_name}")

            file_name = os.path.join(file_path, file_name)
            file_name = os.path.expanduser(file_name)

            if not os.path.exists(os.path.dirname(file_name)):
                try:
                    os.makedirs(file_name, exist_ok=True)
                except FileExistsError:
                    pass

            if os.path.exists(file_name):
                self.api.update_download_log(
                    f"File already exists, skipping download"
                )
                self.api.set_download_progress(current=0, total=0)
                self.finished.emit()
                continue

            size_kb = self.get_size(url)
            self.api.update_download_log(
                f"Downloading {url} of size {size_kb} bytes to {file_name}"
            )

            try:
                headers = {}
                with requests.get(
                    url, headers=headers, stream=True, allow_redirects=True
                ) as r:
                    r.raise_for_status()
                    dir_name = os.path.dirname(file_name)

                    if dir_name != "" and not os.path.exists(dir_name):
                        try:
                            os.makedirs(dir_name, exist_ok=True)
                        except FileExistsError:
                            pass

                    with open(file_name, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if self.is_cancelled:
                                break
                            try:
                                f.write(chunk)
                            except OverflowError:
                                print(
                                    f"OverflowError when writing to {file_name}"
                                )
                                raise
                            self.api.set_download_progress(
                                current=f.tell(), total=size_kb
                            )
                        self.api.update_download_log(
                            f"Finished downloading {file_name}"
                        )
                        self.finished.emit()
            except Exception as e:
                print(f"Failed to download {url}")
                print(e)
                self.failed.emit(e)
                self.api.download_complete()
