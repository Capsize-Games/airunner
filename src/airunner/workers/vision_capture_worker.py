from airunner.workers.worker import Worker


class VisionCaptureWorker(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register("vision_capture_signal", self)
    
    def on_vision_capture_signal(self, message):
        self.add_to_queue(message)

    def handle_message(self, message):
        print("TODO: CAPTURE IMAGE HERE")
        self.emit("vision_captured_signal", message)
