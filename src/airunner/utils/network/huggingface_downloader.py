from typing import Callable
from PySide6.QtCore import QObject, QThread, Signal
from airunner.workers.download_worker import DownloadWorker
from airunner.enums import SignalCode
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.gui.windows.main.settings_mixin import SettingsMixin


class HuggingfaceDownloader(
    MediatorMixin,
    SettingsMixin,
    QObject,
):
    completed = Signal()

    def __init__(self, callback=None):
        super().__init__()
        self.thread = None
        self.worker = None
        self.downloading = False

        self.thread = QThread()
        self.worker = DownloadWorker()
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.worker.finished.connect(
            lambda: self.emit_signal(SignalCode.DOWNLOAD_COMPLETE)
        )
        self.worker.progress.connect(
            lambda current, total: callback(current, total)
        )

        self.logger.debug(f"Starting model download thread")
        self.thread.finished.connect(self.handle_completed)
        self.thread.started.connect(self.worker.download)
        self.thread.start()

    def download_model(
        self,
        requested_path: str,
        requested_file_name: str,
        requested_file_path: str,
        requested_callback: Callable[[int, int], None],
    ):
        self.worker.add_to_queue(
            (
                requested_path,
                requested_file_name,
                requested_file_path,
                requested_callback,
            )
        )

    def handle_completed(self):
        self.completed.emit()
        self.worker.deleteLater()
        self.thread.deleteLater()

    def stop_download(self):
        if self.worker:
            self.worker.cancel()
            self.remove_file()
