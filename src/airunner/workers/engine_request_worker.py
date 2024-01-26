from airunner.enums import EngineRequestCode, SignalCode
from airunner.workers.worker import Worker


class EngineRequestWorker(Worker):
    def __init__(self, prefix="EngineRequestWorker"):
        super().__init__(prefix=prefix)
        self.register(SignalCode.ENGINE_DO_REQUEST_SIGNAL, self.on_engine_do_request_signal)
    
    def on_engine_do_request_signal(self, request):
        self.logger.info("Adding to queue")
        self.add_to_queue(request)
    
    def handle_message(self, request):
        if request["code"] == EngineRequestCode.GENERATE_IMAGE:
            self.emit(SignalCode.SD_REQUEST_SIGNAL, request)
        else:
            self.logger.error(f"Unknown code: {request['code']}")