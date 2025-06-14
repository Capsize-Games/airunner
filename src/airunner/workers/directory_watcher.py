from PySide6.QtCore import QObject, Signal, Slot, QThread

from airunner.utils.application.get_logger import get_logger


class DirectoryWatcher(QObject):
    scan_completed = Signal(bool)

    def __init__(
        self,
        base_path: str,
        scan_function: callable,
        on_scan_completed: callable,
    ):
        super().__init__()
        self.logger = get_logger(__name__)
        self.base_path = base_path
        self._scan_function = scan_function
        self._on_scan_completed = on_scan_completed
        self.scan_completed.connect(self.on_scan_completed)

    def run(self):
        while True:
            force_reload = self._scan_function(self.base_path)
            try:
                self.scan_completed.emit(force_reload)
            except RuntimeError as e:
                self.logger.error(f"Error emitting scan_completed signal: {e}")
            QThread.sleep(1)

    @Slot(bool)
    def on_scan_completed(self, force_reload: bool):
        self._on_scan_completed(force_reload)
