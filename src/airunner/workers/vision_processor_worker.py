from airunner.workers.worker import Worker


class VisionProcessorWorker(Worker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register("vision_process_signal", self)
    
    def on_vision_process_signal(self, message):
        self.add_to_queue(message)
    
    def preprocess(self):
        pass

    def handle_message(self, message):
        print("TODO: USE AI MODEL TO PROCESS IMAGE HERE")
        self.emit("vision_processed_signal", message)
