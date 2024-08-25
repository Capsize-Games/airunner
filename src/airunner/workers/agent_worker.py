import traceback
import torch

from airunner.enums import SignalCode
from airunner.workers.worker import Worker


class AgentWorker(Worker):
    def handle_message(self, message):
        input_ids = message["kwargs"].get("input_ids", None)
        if input_ids is not None:
            if torch.isnan(input_ids).any():
                print("Model output contains NaN values.")
                return None
        try:
            message["model"].generate(**message["kwargs"])
        except Exception as e:
            print("47 An error occurred in model.generate:")
            print(str(e))
            print(traceback.format_exc())
