from airunner.aihandler.enums import EngineRequestCode
from airunner.workers.worker import Worker


class EngineRequestWorker(Worker):
    def __init__(self, prefix="EngineRequestWorker"):
        super().__init__(prefix=prefix)
        self.register("engine_do_request_signal", self)
    
    def on_engine_do_request_signal(self, request):
        self.logger.info("Adding to queue")
        self.add_to_queue(request)
    
    def handle_message(self, request):
        if request["code"] == EngineRequestCode.GENERATE_IMAGE:
            self.emit("sd_request_signal", request)
        else:
            self.logger.error(f"Unknown code: {request['code']}")