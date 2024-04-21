import torch
from airunner.aihandler.stablediffusion.sd_handler import SDHandler
from airunner.enums import QueueType
from airunner.workers.worker import Worker
torch.backends.cuda.matmul.allow_tf32 = True


class SDWorker(Worker):
    queue_type = QueueType.GET_LAST_ITEM

    def __init__(self, prefix="SDWorker"):
        super().__init__(prefix=prefix)
        self.sd = SDHandler()

    def handle_message(self, message):
        self.sd.run()

