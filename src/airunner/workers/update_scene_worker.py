from PyQt6.QtCore import QThread

from airunner.enums import SignalCode
from airunner.settings import SLEEP_TIME_IN_MS
from airunner.workers.worker import Worker


class UpdateSceneWorker(Worker):
    def __init__(self, prefix):
        super().__init__()
        self.scene = None
        self.update_time_in_ms = 0.2
        self.last_update = 0
        self.do_update = False
        self.register(SignalCode.LINES_UPDATED_SIGNAL, self.on_lines_updated_signal)

    def on_lines_updated_signal(self):
        self.do_update = True

    def handle_message(self, message):
        pass

    def run(self):
        self.running = True
        while self.running:
            if self.scene:
                self.scene.update()
            QThread.msleep(SLEEP_TIME_IN_MS)
