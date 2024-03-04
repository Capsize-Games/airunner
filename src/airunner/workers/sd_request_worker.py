import torch
from PyQt6.QtCore import QThread

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
        with torch.inference_mode():
            while self.running:
                self.sd.run()
                QThread.msleep(SLEEP_TIME_IN_MS)


class SDRequestWorker(Worker):
    queue_type = QueueType.GET_LAST_ITEM

    def __init__(self, prefix="SDRequestWorker"):
        super().__init__(prefix=prefix)
        self.register(SignalCode.SD_REQUEST_SIGNAL, self.on_sd_request_signal)
    
    def on_sd_request_signal(self, request):
        self.logger.debug("Request recieved")
        self.add_to_queue(request["message"])
    
    def handle_message(self, message):
        print("HANDLE REQUEST")
        self.logger.debug("Handling message")
        self.emit(SignalCode.SD_ADD_RESPONSE_TO_QUEUE_SIGNAL, {
            'message': message,
            'image_base_path': self.settings["path_settings"]["image_path"]
        })
