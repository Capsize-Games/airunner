from typing import Callable
from PySide6.QtCore import QObject, Signal
from airunner.workers.download_worker import DownloadWorker
from airunner.enums import SignalCode
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin
from airunner.utils.application.create_worker import create_worker


class HuggingfaceDownloader(
    MediatorMixin,
    SettingsMixin,
    QObject,
):
    completed = Signal()

    def __init__(self, callback=None, initialize_gui=True):
        super().__init__()
        self.thread = None
        self.worker = None
        self.downloading = False

        self.worker = create_worker(
            DownloadWorker, initialize_gui=initialize_gui
        )

        # Connect signals
        self.worker.progress.connect(
            lambda current, total: callback(current, total)
        )

        self.logger.debug(f"Starting model download thread")
        self.worker.finished.connect(self.handle_completed)

    def download_model(
        self,
        requested_path: str,
        requested_file_name: str,
        requested_file_path: str,
        requested_callback: Callable[[int, int], None],
    ):
        self.worker.add_to_queue(
            dict(
                requested_path=requested_path,
                requested_file_name=requested_file_name,
                requested_file_path=requested_file_path,
                requested_callback=requested_callback,
            )
        )

    def handle_completed(self):
        self.completed.emit()

    def stop_download(self):
        if self.worker:
            self.worker.cancel()
