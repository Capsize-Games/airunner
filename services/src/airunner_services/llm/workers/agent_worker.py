import traceback
import torch
from typing import Dict

from airunner_services.llm.managers.llm_response import LLMResponse
from airunner_services.workers.worker import Worker


class AgentWorker(Worker):
    def handle_message(self, message: Dict):
        """
        Handle the message and generate the response using the model.
        """
        input_ids = message["kwargs"].get("input_ids", None)
        if input_ids is not None:
            if torch.isnan(input_ids).any():
                print("Model output contains NaN values.")
                return None
        try:
            message["model"].generate(**message["kwargs"])
        except RuntimeError as e:
            self.logger.error(f"RuntimeError: {str(e)}")
            self.api.llm.send_llm_text_streamed_signal(
                LLMResponse(
                    is_first_message=True,
                    is_end_of_message=True,
                    name=message["botname"],
                    is_system_message=True,
                )
            )

        except Exception as e:
            print("47 An error occurred in model.generate:")
            print(str(e))
            print(traceback.format_exc())
