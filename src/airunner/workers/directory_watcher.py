from PySide6.QtCore import QObject, Signal, Slot, QThread


class DirectoryWatcher(QObject):
    scan_completed = Signal(bool)

    def __init__(self, base_path: str, scan_function: callable, on_scan_completed: callable):
        super().__init__()
        self.base_path = base_path
        self._scan_function = scan_function
        self._on_scan_completed = on_scan_completed
        self.scan_completed.connect(self.on_scan_completed)

    def run(self):
        while True:
            force_reload = self._scan_function(self.base_path)
            self.scan_completed.emit(force_reload)
            QThread.sleep(1)
    
    @Slot(bool)
    def on_scan_completed(self, force_reload: bool):
        self._on_scan_completed(force_reload)
