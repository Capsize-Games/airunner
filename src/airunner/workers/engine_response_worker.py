from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class EngineResponseWorker(Worker):
    def __init__(self, prefix="EngineResponseWorker"):
        super().__init__(prefix=prefix)
        self.register(SignalCode.ENGINE_DO_RESPONSE_SIGNAL, self.on_engine_do_response_signal)
    
    def on_engine_do_response_signal(self, request):
        self.logger.info("Adding to queue")
        self.add_to_queue(request)
