import torch
from PySide6.QtCore import QThread

from airunner.aihandler.stablediffusion.sd_handler import SDHandler
from airunner.enums import SignalCode, QueueType
from airunner.settings import SLEEP_TIME_IN_MS
from airunner.workers.worker import Worker

torch.backends.cuda.matmul.allow_tf32 = True


class SDWorker(Worker):
    queue_type = QueueType.GET_LAST_ITEM

    def __init__(self, prefix="SDWorker"):
        super().__init__(prefix=prefix)
        self.sd = SDHandler()

    def run(self):
        self.running = True
        with torch.no_grad():
            while self.running:
                self.sd.run()
                QThread.msleep(SLEEP_TIME_IN_MS)

