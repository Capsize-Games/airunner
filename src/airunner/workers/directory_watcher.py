from PySide6.QtCore import QObject, Signal, QThread


class DirectoryWatcher(QObject):
    scan_completed = Signal(bool)

    def __init__(self, base_path: str, scan_function: callable):
        super().__init__()
        self.base_path = base_path
        self._scan_function = scan_function

    def run(self):
        while True:
            force_reload = self._scan_function(self.base_path)
            self.scan_completed.emit(force_reload)
            QThread.sleep(1)
