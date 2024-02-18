from airunner.enums import SignalCode
from airunner.aihandler.llm.vision_handler import VisionHandler
from airunner.workers.worker import Worker


class VisionProcessorWorker(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register(SignalCode.VISION_STOP_CAPTURE, self.on_stop_vision_capture)
        self.register(SignalCode.VISION_CAPTURE_PROCESS_SIGNAL, self.on_vision_process)
        self.vision_handler = VisionHandler()

    def on_stop_vision_capture(self, _message):
        self.vision_handler.unload()
    
    def on_vision_process(self, message):
        self.add_to_queue(message)

    def handle_message(self, message):
        """
        Process the image and emit the vision processed signal.
        :param message:
        :return:
        """
        message = self.vision_handler.handle_request({
            "request_data": message
        })
        self.emit(SignalCode.VISION_PROCESSED_SIGNAL, message)
