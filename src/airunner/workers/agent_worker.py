import traceback
import torch

from airunner.enums import SignalCode, LLMActionType
from airunner.workers.worker import Worker


class AgentWorker(Worker):
    def handle_message(self, message):
        input_ids = message["kwargs"].get("input_ids", None)
        if input_ids is not None:
            if torch.isnan(input_ids).any():
                print("Model output contains NaN values.")
                return None
        try:
            if self.llm_generator_settings.use_api:
                res = message["model"].stream_complete(
                    prompt=message["prompt"],
                    # do_sample=True,
                    # early_stopping=True,
                    # eta_cutoff=200,
                    # length_penalty=1.0,
                    # max_new_tokens=200,
                    # min_length=1,
                    # no_preat_ngram_size=2,
                    # num_beams=1,
                    # num_return_sequences=1,
                    # repetition_penalty=1.0,
                    # temperature=1.0,
                    # top_k=50,
                    top_p=0.9,
                    # use_cache=True,
                    # streamer=message["kwargs"]["streamer"],
                )
                is_first_message = True
                response = ""
                for r in res:
                    response += r.delta
                    is_first_message = False
                self.emit_signal(
                    SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                    dict(
                        message=response,
                        is_first_message=True,
                        is_end_of_message=True,
                        name=message["botname"],
                        action=LLMActionType.CHAT
                    )
                )
            else:
                try:
                    message["model"].generate(**message["kwargs"])
                except RuntimeError as e:
                    self.logger.error(f"RuntimeError: {str(e)}")
                    self.emit_signal(
                        SignalCode.LLM_TEXT_STREAMED_SIGNAL,
                        dict(
                            message="",
                            is_first_message=True,
                            is_end_of_message=True,
                            name=message["botname"],
                            action=LLMActionType.CHAT
                        )
                    )

        except Exception as e:
            print("47 An error occurred in model.generate:")
            print(str(e))
            print(traceback.format_exc())
