import torch

from airunner.enums import SignalCode
from airunner.workers.worker import Worker

torch.backends.cuda.matmul.allow_tf32 = True


class SDRequestWorker(Worker):
    def __init__(self, prefix="SDRequestWorker"):
        super().__init__(prefix=prefix)
        self.register(SignalCode.SD_REQUEST_SIGNAL, self.on_sd_request_signal)
    
    def on_sd_request_signal(self, request):
        self.logger.info("Request recieved")
        self.add_to_queue(request["message"])
    
    def handle_message(self, message):
        self.logger.info("Handling message")
        self.emit(SignalCode.ADD_SD_RESPONSE_TO_QUEUE_SIGNAL, dict(
            message=message,
            image_base_path=self.settings["path_settings"]["image_path"]
        ))