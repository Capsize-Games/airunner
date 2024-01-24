import torch
from airunner.workers.worker import Worker

torch.backends.cuda.matmul.allow_tf32 = True


class SDRequestWorker(Worker):
    def __init__(self, prefix="SDRequestWorker"):
        super().__init__(prefix=prefix)
        self.register("sd_request_signal", self)
    
    def on_sd_request_signal(self, request):
        self.logger.info("Request recieved")
        self.add_to_queue(request["message"])
    
    def handle_message(self, message):
        self.logger.info("Handling message")
        self.emit("add_sd_response_to_queue_signal", dict(
            message=message,
            image_base_path=self.path_settings["image_path"]
        ))