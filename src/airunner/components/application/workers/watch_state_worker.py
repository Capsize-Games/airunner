from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication


class WatchStateWorker(QObject):
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        self.paused = False

    def run(self):
        QApplication.processEvents()
        self.signal.emit()
